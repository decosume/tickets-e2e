#!/bin/bash

# Unified BugTracker Deployment Script
# This script deploys the complete BugTracker system with unified DynamoDB schema

set -e

echo "🐛 UNIFIED BUG TRACKER DEPLOYMENT"
echo "=================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed. Please install Python3 first."
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
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS credentials verified"
}

# Check if .env file exists
check_env_file() {
    print_status "Checking environment configuration..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating template..."
        cat > .env << EOF
# AWS Configuration
AWS_REGION=us-east-1
DYNAMODB_TABLE=BugTracker

# Slack Configuration
SLACK_BOT_TOKEN=your_slack_bot_token_here
SLACK_CHANNEL_ID=your_slack_channel_id_here

# Zendesk Configuration
ZENDESK_SUBDOMAIN=your_zendesk_subdomain_here
ZENDESK_EMAIL=your_zendesk_email_here
ZENDESK_API_TOKEN=your_zendesk_api_token_here

# Shortcut Configuration
SHORTCUT_API_TOKEN=your_shortcut_api_token_here
EOF
        print_warning "Please edit .env file with your actual API tokens and configuration"
        print_warning "Then run this script again"
        exit 1
    fi
    
    print_success "Environment configuration found"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    pip3 install -r requirements.txt
    print_success "Python dependencies installed"
}

# Deploy Terraform infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Apply deployment
    print_status "Applying Terraform configuration..."
    terraform apply tfplan
    
    # Get outputs
    TABLE_NAME=$(terraform output -raw bug_tracker_table_name)
    TABLE_ARN=$(terraform output -raw bug_tracker_table_arn)
    ROLE_ARN=$(terraform output -raw bug_tracker_access_role_arn)
    
    cd ..
    
    print_success "Infrastructure deployed successfully"
    print_status "Table Name: $TABLE_NAME"
    print_status "Table ARN: $TABLE_ARN"
    print_status "Role ARN: $ROLE_ARN"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test table creation
    if python3 -c "
import boto3
import os
from dotenv import load_dotenv
load_dotenv()

dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
table = dynamodb.Table('BugTracker')
table.load()
print('Table exists and is accessible')
"; then
        print_success "DynamoDB table test passed"
    else
        print_error "DynamoDB table test failed"
        exit 1
    fi
}

# Run initial data ingestion
run_initial_ingestion() {
    print_status "Running initial data ingestion..."
    
    if python3 bug_tracker_dynamodb.py; then
        print_success "Initial data ingestion completed"
    else
        print_warning "Initial data ingestion had issues (this is normal if APIs are not configured)"
    fi
}

# Create sample data for testing
create_sample_data() {
    print_status "Creating sample data for testing..."
    
    python3 -c "
import boto3
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
table = dynamodb.Table('BugTracker')

# Sample Zendesk item
zendesk_item = {
    'PK': 'ZD-12345',
    'SK': 'zendesk#12345',
    'sourceSystem': 'zendesk',
    'priority': 'High',
    'status': 'open',
    'requester': 'user@example.com',
    'assignee': 'agent@example.com',
    'subject': 'Login button not working',
    'createdAt': '2025-08-30T18:00:00Z',
    'updatedAt': '2025-08-30T18:30:00Z'
}

# Sample Slack item
slack_item = {
    'PK': 'ZD-12345',
    'SK': 'slack#9876543210.12345',
    'sourceSystem': 'slack',
    'author': 'U123ABC',
    'text': 'User reports login button not working. ticketId=ZD-12345 priority=High',
    'createdAt': '2025-08-30T17:50:00Z'
}

# Sample Shortcut item
shortcut_item = {
    'PK': 'ZD-12345',
    'SK': 'shortcut#56789',
    'sourceSystem': 'shortcut',
    'shortcut_story_id': 56789,
    'name': 'Bug: Login button not working',
    'state': 'Ready for QA',
    'createdAt': '2025-08-30T18:05:00Z',
    'updatedAt': '2025-08-30T18:20:00Z'
}

# Insert sample data
table.put_item(Item=zendesk_item)
table.put_item(Item=slack_item)
table.put_item(Item=shortcut_item)

print('Sample data created successfully')
"
    
    print_success "Sample data created"
}

# Show next steps
show_next_steps() {
    echo
    echo "🎯 DEPLOYMENT COMPLETE!"
    echo "======================="
    echo
    echo "Next steps:"
    echo "1. Configure your API tokens in the .env file"
    echo "2. Run data ingestion: python3 bug_tracker_dynamodb.py"
    echo "3. Test manual linking: python3 bug_linker.py"
    echo "4. Configure Grafana to connect to DynamoDB"
    echo "5. Set up automated ingestion scheduling"
    echo
    echo "Useful commands:"
    echo "- View table structure: aws dynamodb describe-table --table-name BugTracker"
    echo "- Query sample data: python3 -c \"from bug_tracker_dynamodb import BugTrackerDynamoDB; bt = BugTrackerDynamoDB(); print(bt.get_bug_by_ticket_id('ZD-12345'))\""
    echo "- List unlinked bugs: python3 bug_linker.py (option 3)"
    echo
}

# Main deployment flow
main() {
    echo "Starting unified BugTracker deployment..."
    echo
    
    check_dependencies
    check_aws_credentials
    check_env_file
    install_dependencies
    deploy_infrastructure
    test_deployment
    create_sample_data
    show_next_steps
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"


