#!/bin/bash

# BugTracker Dashboard Deployment Script
# Following the casting-app pattern

set -e

echo "🚀 BUGTRACKER DASHBOARD DEPLOYMENT"
echo "=================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_PROFILE="AdministratorAccess12hr-100142810612"
AWS_REGION="us-west-2"
S3_BUCKET="bugtracker-dashboard-$(date +%s)"
CLOUDFRONT_DISTRIBUTION=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

# Check AWS credentials
check_aws_credentials() {
    print_status "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        print_error "AWS credentials not configured for profile $AWS_PROFILE"
        print_error "Please run 'aws sso login --profile $AWS_PROFILE' first"
        exit 1
    fi
    
    print_success "AWS credentials verified"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Node.js dependencies..."
    
    if [ ! -f "package.json" ]; then
        print_error "package.json not found. Please run this script from the dashboard directory."
        exit 1
    fi
    
    npm install
    
    print_success "Dependencies installed successfully"
}

# Build the application
build_application() {
    print_status "Building Next.js application..."
    
    # Set environment variables
    export AWS_REGION=$AWS_REGION
    export AWS_PROFILE=$AWS_PROFILE
    
    # Build the application
    npm run build
    
    print_success "Application built successfully"
}

# Deploy to AWS S3
deploy_to_s3() {
    print_status "Deploying to AWS S3..."
    
    # Create S3 bucket
    print_status "Creating S3 bucket: $S3_BUCKET"
    aws s3 mb s3://$S3_BUCKET --profile $AWS_PROFILE --region $AWS_REGION
    
    # Configure S3 bucket for static website hosting
    aws s3 website s3://$S3_BUCKET \
        --index-document index.html \
        --error-document 404.html \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Upload files to S3
    print_status "Uploading dashboard files to S3..."
    aws s3 sync out/ s3://$S3_BUCKET \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --delete
    
    # Get the website URL
    WEBSITE_URL=$(aws s3api get-bucket-website --bucket $S3_BUCKET --profile $AWS_PROFILE --region $AWS_REGION --query 'WebsiteEndpoint' --output text)
    
    print_success "Dashboard deployed to AWS!"
    print_success "Website URL: http://$WEBSITE_URL"
    print_success "S3 Bucket: $S3_BUCKET"
}

# Deploy locally
deploy_locally() {
    print_status "Starting local development server..."
    
    # Check if port 3000 is available
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
        print_warning "Port 3000 is already in use. Using port 3001 instead."
        export PORT=3001
    fi
    
    print_success "Starting server on port ${PORT:-3000}..."
    print_success "Dashboard will be available at: http://localhost:${PORT:-3000}"
    print_success "Press Ctrl+C to stop the server"
    
    # Start the server
    npm run dev
}

# Test the application
test_application() {
    print_status "Testing application..."
    
    # Run linting
    print_status "Running ESLint..."
    npm run lint
    
    # Run type checking
    print_status "Running TypeScript check..."
    npx tsc --noEmit
    
    print_success "Application tests passed"
}

# Show deployment options
show_options() {
    echo
    echo "🎯 DEPLOYMENT OPTIONS"
    echo "===================="
    echo
    echo "1. Deploy locally (development)"
    echo "2. Deploy to AWS (production)"
    echo "3. Build only"
    echo "4. Test only"
    echo "5. Install dependencies only"
    echo
    read -p "Choose an option (1-5): " choice
    
    case $choice in
        1)
            check_dependencies
            check_aws_credentials
            install_dependencies
            deploy_locally
            ;;
        2)
            check_dependencies
            check_aws_credentials
            install_dependencies
            build_application
            deploy_to_s3
            ;;
        3)
            check_dependencies
            install_dependencies
            build_application
            ;;
        4)
            check_dependencies
            install_dependencies
            test_application
            ;;
        5)
            check_dependencies
            install_dependencies
            print_success "Dependencies installed. Run 'npm run dev' to start the server."
            ;;
        *)
            print_error "Invalid option. Please choose 1-5."
            exit 1
            ;;
    esac
}

# Main deployment flow
main() {
    echo "Starting BugTracker Dashboard deployment..."
    echo
    
    if [ "$1" = "aws" ]; then
        check_dependencies
        check_aws_credentials
        install_dependencies
        build_application
        deploy_to_s3
    elif [ "$1" = "local" ]; then
        check_dependencies
        check_aws_credentials
        install_dependencies
        deploy_locally
    elif [ "$1" = "build" ]; then
        check_dependencies
        install_dependencies
        build_application
    elif [ "$1" = "test" ]; then
        check_dependencies
        install_dependencies
        test_application
    elif [ "$1" = "install" ]; then
        check_dependencies
        install_dependencies
    else
        show_options
    fi
}

# Run main function
main "$@"
