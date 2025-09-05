#!/bin/bash

# Simplified BugTracker Deployment Script using AWS CLI
# This script creates the BugTracker DynamoDB table directly using AWS CLI

set -e

echo "🐛 UNIFIED BUG TRACKER DEPLOYMENT (AWS CLI)"
echo "============================================"
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

# Check if table exists
check_table_exists() {
    print_status "Checking if BugTracker table exists..."
    
    if aws dynamodb describe-table --table-name BugTracker --profile $AWS_PROFILE --region $AWS_REGION &> /dev/null; then
        print_success "BugTracker table already exists"
        return 0
    else
        print_status "BugTracker table does not exist, will create it"
        return 1
    fi
}

# Create the BugTracker table
create_table() {
    print_status "Creating BugTracker DynamoDB table..."
    
    # Create table definition JSON
    cat > table-definition.json << 'EOF'
{
    "TableName": "BugTracker",
    "AttributeDefinitions": [
        {
            "AttributeName": "PK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "SK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "priority",
            "AttributeType": "S"
        },
        {
            "AttributeName": "state",
            "AttributeType": "S"
        },
        {
            "AttributeName": "sourceSystem",
            "AttributeType": "S"
        },
        {
            "AttributeName": "createdAt",
            "AttributeType": "S"
        }
    ],
    "KeySchema": [
        {
            "AttributeName": "PK",
            "KeyType": "HASH"
        },
        {
            "AttributeName": "SK",
            "KeyType": "RANGE"
        }
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "priority-index",
            "KeySchema": [
                {
                    "AttributeName": "priority",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "createdAt",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            }
        },
        {
            "IndexName": "state-index",
            "KeySchema": [
                {
                    "AttributeName": "state",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "createdAt",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            }
        },
        {
            "IndexName": "source-index",
            "KeySchema": [
                {
                    "AttributeName": "sourceSystem",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "createdAt",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            }
        }
    ],
    "BillingMode": "PAY_PER_REQUEST"
}
EOF
    
    aws dynamodb create-table \
        --cli-input-json file://table-definition.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Clean up temporary file
    rm table-definition.json
    
    print_success "BugTracker table created successfully"
}

# Wait for table to be active
wait_for_table() {
    print_status "Waiting for table to become active..."
    
    aws dynamodb wait table-exists \
        --table-name BugTracker \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_success "Table is now active"
}

# Create sample data
create_sample_data() {
    print_status "Creating sample data for testing..."
    
    # Sample Zendesk item
    aws dynamodb put-item \
        --table-name BugTracker \
        --item '{
            "PK": {"S": "ZD-12345"},
            "SK": {"S": "zendesk#12345"},
            "sourceSystem": {"S": "zendesk"},
            "priority": {"S": "High"},
            "status": {"S": "open"},
            "requester": {"S": "user@example.com"},
            "assignee": {"S": "agent@example.com"},
            "subject": {"S": "Login button not working"},
            "createdAt": {"S": "2025-08-30T18:00:00Z"},
            "updatedAt": {"S": "2025-08-30T18:30:00Z"}
        }' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Sample Slack item
    aws dynamodb put-item \
        --table-name BugTracker \
        --item '{
            "PK": {"S": "ZD-12345"},
            "SK": {"S": "slack#9876543210.12345"},
            "sourceSystem": {"S": "slack"},
            "author": {"S": "U123ABC"},
            "text": {"S": "User reports login button not working. ticketId=ZD-12345 priority=High"},
            "createdAt": {"S": "2025-08-30T17:50:00Z"}
        }' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    # Sample Shortcut item
    aws dynamodb put-item \
        --table-name BugTracker \
        --item '{
            "PK": {"S": "ZD-12345"},
            "SK": {"S": "shortcut#56789"},
            "sourceSystem": {"S": "shortcut"},
            "shortcut_story_id": {"N": "56789"},
            "name": {"S": "Bug: Login button not working"},
            "state": {"S": "Ready for QA"},
            "createdAt": {"S": "2025-08-30T18:05:00Z"},
            "updatedAt": {"S": "2025-08-30T18:20:00Z"}
        }' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_success "Sample data created successfully"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test query by ticket ID
    result=$(aws dynamodb query \
        --table-name BugTracker \
        --key-condition-expression "PK = :ticket_id" \
        --expression-attribute-values '{":ticket_id":{"S":"ZD-12345"}}' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION)
    
    count=$(echo "$result" | jq '.Count')
    print_success "Found $count records for ticket ZD-12345"
    
    # Test GSI query
    gsi_result=$(aws dynamodb query \
        --table-name BugTracker \
        --index-name priority-index \
        --key-condition-expression "priority = :priority" \
        --expression-attribute-values '{":priority":{"S":"High"}}' \
        --profile $AWS_PROFILE \
        --region $AWS_REGION)
    
    gsi_count=$(echo "$gsi_result" | jq '.Count')
    print_success "Found $gsi_count High priority bugs via GSI"
}

# Update environment variables
update_env() {
    print_status "Updating .env file with AWS configuration..."
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        # Update AWS region in .env
        sed -i '' 's/AWS_REGION=.*/AWS_REGION=us-west-2/' .env
        print_success "Updated .env file with AWS region"
    else
        print_warning ".env file not found, please create it with your API tokens"
    fi
}

# Show next steps
show_next_steps() {
    echo
    echo "🎯 DEPLOYMENT COMPLETE!"
    echo "======================="
    echo
    echo "Next steps:"
    echo "1. Run data ingestion: python3 bug_tracker_dynamodb.py"
    echo "2. Test manual linking: python3 bug_linker.py"
    echo "3. Configure Grafana to connect to DynamoDB"
    echo "4. Set up automated ingestion scheduling"
    echo
    echo "Useful commands:"
    echo "- View table structure: aws dynamodb describe-table --table-name BugTracker --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- Query sample data: aws dynamodb query --table-name BugTracker --key-condition-expression 'PK = :ticket_id' --expression-attribute-values '{':ticket_id':{'S':'ZD-12345'}}' --profile $AWS_PROFILE --region $AWS_REGION"
    echo "- List unlinked bugs: python3 bug_linker.py (option 3)"
    echo
}

# Main deployment flow
main() {
    echo "Starting unified BugTracker deployment with AWS CLI..."
    echo
    
    update_env
    
    if check_table_exists; then
        print_warning "Table already exists, skipping creation"
    else
        create_table
        wait_for_table
    fi
    
    create_sample_data
    test_deployment
    show_next_steps
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"
