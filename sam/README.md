# SAM-Based BugTracker Deployment

This directory contains the Serverless Application Model (SAM) implementation of the unified BugTracker system, following the same patterns used in the casting-deployments project.

## 🏗️ Architecture Overview

### Serverless Components

1. **DynamoDB Table**: `BugTracker-{Environment}` with unified schema
2. **Lambda Functions**:
   - `BugTrackerIngestion`: Scheduled data ingestion from APIs
   - `BugTrackerLinker`: Manual bug linking operations
   - `BugTrackerQuery`: Query operations for dashboards
3. **API Gateway**: REST API for Lambda function access
4. **CloudWatch**: Logging and monitoring
5. **SNS**: Notifications for high priority bugs

### Unified Schema Implementation

The SAM template implements the exact DynamoDB schema from the design images:

- **Primary Key (PK)**: `ticketId` (e.g., `ZD-12345`, `SC-56789`, `SL-9876543210.12345`)
- **Sort Key (SK)**: `sourceSystem#recordId` (e.g., `zendesk#12345`, `slack#9876543210.12345`)
- **Secondary Indexes**:
  - `priority-index`: Query bugs by priority
  - `state-index`: Query bugs by state/status
  - `source-index`: Query bugs by source system

## 📁 File Structure

```
sam/
├── template.yaml              # SAM CloudFormation template
├── src/
│   ├── bug_tracker_ingestion.py  # Lambda function for data ingestion
│   ├── bug_tracker_linker.py     # Lambda function for manual linking
│   ├── bug_tracker_query.py      # Lambda function for queries
│   └── requirements.txt           # Python dependencies
├── deploy.sh                   # Deployment script
└── README.md                   # This file
```

## 🚀 Quick Deployment

### Prerequisites

1. **AWS SAM CLI**: Install from [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
2. **AWS CLI**: Install and configure with SSO
3. **Python 3.9+**: For Lambda runtime
4. **jq**: For JSON parsing in deployment script

### Deployment Steps

1. **Login to AWS SSO**:
   ```bash
   aws sso login --profile AdministratorAccess12hr-100142810612
   ```

2. **Deploy the stack**:
   ```bash
   cd sam
   ./deploy.sh
   ```

The deployment script will:
- Check dependencies and AWS credentials
- Build the SAM application
- Deploy the CloudFormation stack
- Test the deployment
- Clean up build artifacts

## 🔧 Configuration

### Environment Variables

The SAM template uses parameters that can be set via:

1. **Command line** during deployment
2. **Environment file** (`.env` in parent directory)
3. **AWS Systems Manager Parameter Store**

### Required Parameters

- `Environment`: Environment name (dev, staging, prod)
- `SlackBotToken`: Slack Bot Token for API access
- `SlackChannelId`: Slack Channel ID for monitoring
- `ZendeskSubdomain`: Zendesk subdomain
- `ZendeskEmail`: Zendesk email for API access
- `ZendeskApiToken`: Zendesk API Token
- `ShortcutApiToken`: Shortcut API Token

## 🔄 Lambda Functions

### BugTrackerIngestion Function

**Purpose**: Scheduled data ingestion from Slack, Zendesk, and Shortcut APIs

**Schedule**: Runs every hour via CloudWatch Events

**Features**:
- Fetches data from all three sources
- Implements unified schema upsert strategy
- Handles synthetic ticket IDs for Slack messages
- Updates existing records with new status/priority

### BugTrackerLinker Function

**Purpose**: Manual bug linking operations via API Gateway

**Endpoints**:
- `POST /link-bugs`: Link bugs by updating ticket ID
- `POST /create-synthetic-link`: Create synthetic ticket links

**Features**:
- Implements one-time migration strategy
- Supports cross-system bug linking
- Handles synthetic ticket creation

### BugTrackerQuery Function

**Purpose**: Query operations for dashboards and analytics

**Endpoints**:
- `GET /query-bugs`: Query bugs by various criteria

**Query Types**:
- `by_ticket_id`: Get all records for a specific ticket
- `by_priority`: Get bugs by priority using GSI
- `by_state`: Get bugs by state using GSI
- `by_source`: Get bugs by source system using GSI
- `summary`: Get summary statistics
- `time_series`: Get time series data

## 📊 Monitoring and Analytics

### CloudWatch Integration

- **Log Groups**: Automatic log groups for each Lambda function
- **Metrics**: Custom metrics for bug counts and ingestion success
- **Alarms**: High priority bug threshold alarms

### SNS Notifications

- **Topic**: `BugTrackerNotifications-{Environment}`
- **Alarms**: High priority bug count alerts
- **Integration**: Can be extended for Slack/email notifications

### Grafana Integration

The DynamoDB table can be connected to Grafana using:

1. **DynamoDB Data Source Plugin**
2. **Secondary Index Queries**:
   - `priority-index` for priority-based dashboards
   - `state-index` for workflow dashboards
   - `source-index` for source system dashboards

## 🔍 API Usage Examples

### Query Bugs by Priority

```bash
curl -X GET "https://{api-id}.execute-api.us-west-2.amazonaws.com/dev/query-bugs" \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "by_priority",
    "params": {
      "priority": "High"
    }
  }'
```

### Link Bugs Manually

```bash
curl -X POST "https://{api-id}.execute-api.us-west-2.amazonaws.com/dev/link-bugs" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "link_bugs",
    "old_ticket_id": "SL-1234567890.12345",
    "new_ticket_id": "ZD-12345"
  }'
```

### Get Bug Summary

```bash
curl -X GET "https://{api-id}.execute-api.us-west-2.amazonaws.com/dev/query-bugs" \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "summary"
  }'
```

## 🛠️ Development

### Local Testing

```bash
# Build locally
sam build

# Test locally
sam local invoke BugTrackerIngestionFunction --event events/ingestion-event.json

# Start local API
sam local start-api
```

### Lambda Function Development

Each Lambda function follows these patterns:

1. **Error Handling**: Comprehensive try-catch blocks
2. **Logging**: Structured logging with CloudWatch
3. **Input Validation**: Parameter validation and error responses
4. **Response Format**: Consistent JSON response structure

## 🔄 Update Strategy

The SAM implementation follows the exact update strategy from the design:

1. **Scheduled Ingestion**: Hourly Lambda execution
2. **Upsert Operations**: DynamoDB put_item for updates
3. **Synthetic IDs**: SL-{msgId} for unlinked Slack messages
4. **Manual Linking**: API endpoints for PM operations
5. **Cross-System Support**: Unified ticket ID across all sources

## 📈 Scaling

### DynamoDB Scaling

- **Billing Mode**: PAY_PER_REQUEST (auto-scaling)
- **Read/Write Capacity**: Automatically scales based on demand
- **Secondary Indexes**: Optimized for common query patterns

### Lambda Scaling

- **Concurrency**: Automatic scaling based on invocation rate
- **Memory**: Configurable memory allocation
- **Timeout**: 5-minute timeout for long-running operations

## 🔒 Security

### IAM Permissions

- **Least Privilege**: Minimal required permissions for each function
- **DynamoDB Access**: Specific table and index permissions
- **API Gateway**: CORS-enabled with proper headers

### Environment Variables

- **Secure Parameters**: API tokens stored as secure parameters
- **No Hardcoding**: All sensitive data externalized

## 🚨 Troubleshooting

### Common Issues

1. **SAM Build Failures**: Check Python dependencies in requirements.txt
2. **Deployment Failures**: Verify AWS credentials and permissions
3. **Lambda Timeouts**: Increase timeout for long-running operations
4. **DynamoDB Errors**: Check table permissions and capacity

### Debugging

```bash
# View CloudWatch logs
aws logs tail /aws/lambda/BugTrackerIngestion-dev --follow --profile AdministratorAccess12hr-100142810612

# Test Lambda function
aws lambda invoke --function-name BugTrackerIngestion-dev --payload '{}' response.json --profile AdministratorAccess12hr-100142810612

# View stack events
aws cloudformation describe-stack-events --stack-name BugTracker --profile AdministratorAccess12hr-100142810612
```

## 📝 Next Steps

1. **Deploy the stack** using the deployment script
2. **Configure API tokens** in the .env file
3. **Test the Lambda functions** manually
4. **Set up Grafana dashboards** using the DynamoDB data source
5. **Configure monitoring** and alerting
6. **Train team** on manual linking process
7. **Monitor performance** and optimize as needed


