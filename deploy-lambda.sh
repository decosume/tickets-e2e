#!/bin/bash

# Lambda Deployment Script for BugTracker System
# This script deploys Lambda functions and other components

set -e

echo "🐛 LAMBDA DEPLOYMENT FOR BUG TRACKER"
echo "===================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# AWS Profile to use
AWS_PROFILE="AdministratorAccess12hr-100142810612"
AWS_REGION="us-west-2"
ENVIRONMENT="dev"

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

# Create IAM Role for Lambda
create_iam_role() {
    print_status "Creating IAM Role for Lambda functions..."
    
    # Create trust policy
    cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name BugTrackerLambdaRole-$ENVIRONMENT \
        --assume-role-policy-document file://trust-policy.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION

    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name BugTrackerLambdaRole-$ENVIRONMENT \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
        --profile $AWS_PROFILE \
        --region $AWS_REGION

    # Create DynamoDB access policy
    cat > dynamodb-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:$AWS_REGION:935779638706:table/BugTracker-$ENVIRONMENT",
        "arn:aws:dynamodb:$AWS_REGION:935779638706:table/BugTracker-$ENVIRONMENT/index/*"
      ]
    }
  ]
}
EOF

    # Attach DynamoDB policy
    aws iam put-role-policy \
        --role-name BugTrackerLambdaRole-$ENVIRONMENT \
        --policy-name BugTrackerDynamoDBAccess \
        --policy-document file://dynamodb-policy.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION

    print_success "IAM Role created successfully"
}

# Deploy Lambda functions
deploy_lambda_functions() {
    print_status "Deploying Lambda functions..."
    
    # Install dependencies
    cd lambdas
    pip install -r requirements.txt -t .
    cd ..
    
    # Create deployment package for ingestion function
    print_status "Creating deployment package for ingestion function..."
    cd lambdas
    zip -r ../bug_tracker_ingestion.zip .
    cd ..
    
    # Get the role ARN
    ROLE_ARN=$(aws iam get-role --role-name BugTrackerLambdaRole-$ENVIRONMENT --profile $AWS_PROFILE --region $AWS_REGION --query 'Role.Arn' --output text)
    
    # Create Lambda function
    aws lambda create-function \
        --function-name BugTrackerIngestion-$ENVIRONMENT \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler bug_tracker_ingestion.lambda_handler \
        --zip-file fileb://bug_tracker_ingestion.zip \
        --timeout 300 \
        --environment Variables='{AWS_REGION='$AWS_REGION',DYNAMODB_TABLE=BugTracker-'$ENVIRONMENT'}' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_success "Lambda functions deployed successfully"
}

# Create CloudWatch Events rule
create_scheduled_rule() {
    print_status "Creating CloudWatch Events rule for scheduled ingestion..."
    
    # Create the rule
    aws events put-rule \
        --name BugTrackerIngestionSchedule-$ENVIRONMENT \
        --schedule-expression "rate(1 hour)" \
        --description "Scheduled data ingestion for BugTracker" \
        --state ENABLED \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Get the Lambda function ARN
    FUNCTION_ARN=$(aws lambda get-function --function-name BugTrackerIngestion-$ENVIRONMENT --profile $AWS_PROFILE --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)
    
    # Add Lambda as target
    aws events put-targets \
        --rule BugTrackerIngestionSchedule-$ENVIRONMENT \
        --targets "Id"="BugTrackerIngestionTarget","Arn"="$FUNCTION_ARN" \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Add permission for CloudWatch Events to invoke Lambda
    aws lambda add-permission \
        --function-name BugTrackerIngestion-$ENVIRONMENT \
        --statement-id BugTrackerIngestionPermission \
        --action lambda:InvokeFunction \
        --principal events.amazonaws.com \
        --source-arn $(aws events describe-rule --name BugTrackerIngestionSchedule-$ENVIRONMENT --profile $AWS_PROFILE --region $AWS_REGION --query 'Arn' --output text) \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_success "CloudWatch Events rule created successfully"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test the Lambda function
    aws lambda invoke \
        --function-name BugTrackerIngestion-$ENVIRONMENT \
        --payload '{"test": "data"}' \
        response.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    if [ $? -eq 0 ]; then
        print_success "Lambda function test successful"
        cat response.json
    else
        print_warning "Lambda function test failed"
    fi
}

# Clean up
cleanup() {
    print_status "Cleaning up temporary files..."
    
    rm -f trust-policy.json
    rm -f dynamodb-policy.json
    rm -f bug_tracker_ingestion.zip
    rm -f response.json
    rm -rf lambdas/*.pyc
    rm -rf lambdas/__pycache__
    rm -rf lambdas/boto3*
    rm -rf lambdas/requests*
    rm -rf lambdas/urllib3*
    rm -rf lambdas/certifi*
    rm -rf lambdas/charset_normalizer*
    rm -rf lambdas/idna*
    
    print_success "Cleanup completed"
}

# Show deployment summary
show_summary() {
    echo
    echo "🎯 LAMBDA DEPLOYMENT COMPLETE!"
    echo "============================="
    echo
    echo "Deployed Resources:"
    echo "- DynamoDB Table: BugTracker-$ENVIRONMENT"
    echo "- IAM Role: BugTrackerLambdaRole-$ENVIRONMENT"
    echo "- Lambda Function: BugTrackerIngestion-$ENVIRONMENT"
    echo "- CloudWatch Events Rule: BugTrackerIngestionSchedule-$ENVIRONMENT"
    echo
    echo "Next steps:"
    echo "1. Configure environment variables with API tokens"
    echo "2. Test the Lambda function manually"
    echo "3. Set up monitoring and alerting"
    echo "4. Configure Grafana for visualization"
    echo
    echo "Useful commands:"
    echo "- Test Lambda: aws lambda invoke --function-name BugTrackerIngestion-$ENVIRONMENT --payload '{}' response.json --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- View logs: aws logs describe-log-groups --log-group-name-prefix /aws/lambda/BugTracker --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- Update function: aws lambda update-function-code --function-name BugTrackerIngestion-$ENVIRONMENT --zip-file fileb://bug_tracker_ingestion.zip --profile $AWS_PROFILE --region $AWS_REGION"
    echo
}

# Main deployment flow
main() {
    echo "Starting Lambda deployment for BugTracker..."
    echo
    
    check_aws_credentials
    create_iam_role
    deploy_lambda_functions
    create_scheduled_rule
    test_deployment
    cleanup
    show_summary
    
    print_success "Lambda deployment completed successfully!"
}

# Run main function
main "$@"


