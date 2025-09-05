#!/bin/bash

# SAM Deployment Script for Unified BugTracker System
# This script deploys the complete BugTracker stack using SAM

set -e

echo "🐛 SAM DEPLOYMENT FOR UNIFIED BUG TRACKER"
echo "========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="BugTracker"
ENVIRONMENT="dev"
AWS_REGION="us-west-2"
AWS_PROFILE="AdministratorAccess12hr-100142810612"

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
    
    if ! command -v sam &> /dev/null; then
        print_error "SAM CLI is not installed. Please install AWS SAM CLI first."
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

# Build SAM application
build_sam() {
    print_status "Building SAM application..."
    
    cd src
    pip install -r requirements.txt -t .
    cd ..
    
    sam build --profile $AWS_PROFILE --region $AWS_REGION
    
    print_success "SAM application built successfully"
}

# Deploy SAM application
deploy_sam() {
    print_status "Deploying SAM application..."
    
    # Check if .env file exists and extract parameters
    if [ -f "../.env" ]; then
        print_status "Loading parameters from .env file..."
        
        # Source the .env file to get variables
        source ../.env
        
        # Deploy with parameters
        sam deploy \
            --stack-name $STACK_NAME \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides \
                Environment=$ENVIRONMENT \
                SlackBotToken="$SLACK_BOT_TOKEN" \
                SlackChannelId="$SLACK_CHANNEL_ID" \
                ZendeskSubdomain="$ZENDESK_SUBDOMAIN" \
                ZendeskEmail="$ZENDESK_EMAIL" \
                ZendeskApiToken="$ZENDESK_API_TOKEN" \
                ShortcutApiToken="$SHORTCUT_API_TOKEN" \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
    else
        print_warning ".env file not found, deploying with default parameters"
        
        # Deploy without parameters (will use defaults)
        sam deploy \
            --stack-name $STACK_NAME \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides Environment=$ENVIRONMENT \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
    fi
    
    print_success "SAM application deployed successfully"
}

# Get stack outputs
get_outputs() {
    print_status "Getting stack outputs..."
    
    outputs=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    echo "$outputs" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'
    
    print_success "Stack outputs retrieved"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Get the API Gateway URL
    api_url=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`BugTrackerApiUrl`].OutputValue' \
        --output text)
    
    if [ "$api_url" != "None" ] && [ "$api_url" != "" ]; then
        print_status "Testing API Gateway endpoint: $api_url"
        
        # Test the query endpoint
        response=$(curl -s "$api_url/query-bugs" \
            -H "Content-Type: application/json" \
            -d '{"query_type": "summary"}')
        
        if [ $? -eq 0 ]; then
            print_success "API Gateway test successful"
            echo "Response: $response"
        else
            print_warning "API Gateway test failed (this is normal if no data exists yet)"
        fi
    else
        print_warning "API Gateway URL not found in stack outputs"
    fi
}

# Show next steps
show_next_steps() {
    echo
    echo "🎯 SAM DEPLOYMENT COMPLETE!"
    echo "=========================="
    echo
    echo "Next steps:"
    echo "1. Test the Lambda functions manually"
    echo "2. Configure Grafana to connect to DynamoDB"
    echo "3. Set up monitoring and alerting"
    echo "4. Configure automated ingestion scheduling"
    echo
    echo "Useful commands:"
    echo "- View stack details: aws cloudformation describe-stacks --stack-name $STACK_NAME --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- View DynamoDB table: aws dynamodb describe-table --table-name BugTracker-$ENVIRONMENT --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- Test Lambda functions: aws lambda invoke --function-name BugTrackerIngestion-$ENVIRONMENT --profile $AWS_PROFILE --region $AWS_REGION response.json"
    echo "- View CloudWatch logs: aws logs describe-log-groups --log-group-name-prefix /aws/lambda/BugTracker --profile $AWS_PROFILE --region $AWS_REGION"
    echo
}

# Clean up build artifacts
cleanup() {
    print_status "Cleaning up build artifacts..."
    
    rm -rf .aws-sam
    rm -rf src/*.pyc
    rm -rf src/__pycache__
    rm -rf src/boto3*
    rm -rf src/requests*
    rm -rf src/urllib3*
    rm -rf src/certifi*
    rm -rf src/charset_normalizer*
    rm -rf src/idna*
    
    print_success "Build artifacts cleaned up"
}

# Main deployment flow
main() {
    echo "Starting SAM deployment for BugTracker..."
    echo
    
    check_dependencies
    check_aws_credentials
    build_sam
    deploy_sam
    get_outputs
    test_deployment
    cleanup
    show_next_steps
    
    print_success "SAM deployment completed successfully!"
}

# Run main function
main "$@"


