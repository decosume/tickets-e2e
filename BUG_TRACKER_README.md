# Unified BugTracker DynamoDB Implementation

This implementation follows the unified bug tracking schema shown in the design images, creating a single DynamoDB table that can store bugs from multiple sources (Slack, Zendesk, Shortcut) under unified ticket IDs.

## 🏗️ Architecture Overview

### Table Schema
- **Table Name**: `BugTracker`
- **Primary Key (PK)**: `ticketId` (e.g., `ZD-12345`, `SC-56789`, `SL-9876543210.12345`)
- **Sort Key (SK)**: `sourceSystem#recordId` (e.g., `zendesk#12345`, `slack#9876543210.12345`)

### Secondary Indexes
1. **priority-index**: Query bugs by priority (High, Medium, Low, Critical)
2. **state-index**: Query bugs by state/status (Ready for Dev, In Progress, QA, etc.)
3. **source-index**: Query bugs by source system (slack, zendesk, shortcut)

## 📁 Files Overview

### Core Implementation
- `bug_tracker_dynamodb.py` - Main implementation with unified schema
- `bug_linker.py` - Utility for manually linking bugs across systems
- `terraform/bug-tracker-dynamodb.tf` - Infrastructure as Code

### Legacy Files (for reference)
- `support-data-ingestion.py` - Original stub-based implementation
- `dynamodb_data_storage.py` - Alternative implementation with separate data types

## 🚀 Quick Start

### 1. Deploy Infrastructure
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 2. Set Environment Variables
Create a `.env` file:
```env
AWS_REGION=us-east-1
DYNAMODB_TABLE=BugTracker
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_channel_id
ZENDESK_SUBDOMAIN=your_subdomain
ZENDESK_EMAIL=your_email
ZENDESK_API_TOKEN=your_token
SHORTCUT_API_TOKEN=your_token
```

### 3. Run Data Ingestion
```bash
python bug_tracker_dynamodb.py
```

### 4. Link Bugs Manually (if needed)
```bash
python bug_linker.py
```

## 🔄 Update Strategy

The implementation follows the update strategy from the design:

1. **Each API fetch** → `upsert record` into DynamoDB
2. **If record exists** → update `status`, `priority`, `updatedAt`
3. **If new** → insert
4. **If Slack has no `ticketId`** → create synthetic `SL-<msgId>`
5. **When PM later links a real `ZD-####`** → update `PK` (one-time migration)

## 📊 Example Data Structure

### Zendesk Item
```json
{
  "PK": "ZD-12345",
  "SK": "zendesk#12345",
  "sourceSystem": "zendesk",
  "priority": "High",
  "status": "open",
  "requester": "user@example.com",
  "assignee": "agent@example.com",
  "subject": "Login button not working",
  "createdAt": "2025-08-30T18:00:00Z",
  "updatedAt": "2025-08-30T18:30:00Z"
}
```

### Slack Item (linked manually)
```json
{
  "PK": "ZD-12345",
  "SK": "slack#9876543210.12345",
  "sourceSystem": "slack",
  "author": "U123ABC",
  "text": "User reports login button not working. ticketId=ZD-12345 priority=High",
  "createdAt": "2025-08-30T17:50:00Z"
}
```

### Shortcut Item
```json
{
  "PK": "ZD-12345",
  "SK": "shortcut#56789",
  "sourceSystem": "shortcut",
  "shortcut_story_id": 56789,
  "name": "Bug: Login button not working",
  "state": "Ready for QA",
  "createdAt": "2025-08-30T18:05:00Z",
  "updatedAt": "2025-08-30T18:20:00Z"
}
```

## 🔍 Query Examples

### Grafana Queries
1. **Count bugs by priority**: Use `priority-index`
2. **Count bugs by state/status**: Use `state-index`
3. **Time series of new bugs**: Query by `createdAt`
4. **Drill-down for a bug**: Query by `PK = ticketId`

### Python Query Examples
```python
# Get all records for a specific ticket
records = dynamodb.get_bug_by_ticket_id("ZD-12345")

# Get all High priority bugs
high_priority_bugs = dynamodb.get_bugs_by_priority("High")

# Get all bugs in QA
qa_bugs = dynamodb.get_bugs_by_state("Ready for QA")

# Get all bugs from Slack
slack_bugs = dynamodb.get_bugs_by_source("slack")
```

## 🔗 Manual Linking Process

When a Project Manager needs to link bugs across systems:

1. **Run the linker utility**:
   ```bash
   python bug_linker.py
   ```

2. **Find unlinked Slack bugs**:
   - Option 3: List unlinked Slack bugs

3. **Link to Zendesk ticket**:
   - Option 4: Create synthetic ticket link
   - Enter Slack message ID and Zendesk ticket ID

4. **Verify the link**:
   - Option 1: Show bug summary by ticket ID

## 🎯 Benefits of Unified Schema

1. **Single Source of Truth**: All bug information in one table
2. **Cross-System Linking**: Manual linking via unified `ticketId`
3. **Rich Querying**: Multiple GSIs for different views
4. **Scalable**: Pay-per-request billing
5. **Real-time Updates**: Periodic refresh reflects changes live

## 🔧 Configuration

### AWS Permissions
The Terraform configuration creates an IAM role with these permissions:
- `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`
- `dynamodb:DeleteItem`, `dynamodb:Query`, `dynamodb:Scan`
- Access to table and all indexes

### Environment Variables
All API tokens and configuration are loaded from environment variables or `.env` file.

## 📈 Monitoring and Analytics

### Grafana Dashboard Setup
1. Configure DynamoDB data source in Grafana
2. Create queries using the secondary indexes
3. Set up automated ingestion scheduling
4. Monitor bug trends and status changes

### Key Metrics
- Bugs by priority distribution
- Bugs by state/status workflow
- Bugs by source system
- Time series of new bugs
- Cross-system linking success rate

## 🚨 Error Handling

The implementation includes comprehensive error handling:
- API failures (Slack, Zendesk, Shortcut)
- DynamoDB operation failures
- Invalid data formats
- Missing environment variables

## 🔄 Periodic Refresh

The system supports periodic refresh:
- Each run pulls from APIs
- Upserts into DynamoDB
- Grafana reflects changes live
- Manual linking updates propagate immediately

## 📝 Next Steps

1. **Deploy the infrastructure** using Terraform
2. **Run initial data ingestion** to populate the table
3. **Configure Grafana** to connect to DynamoDB
4. **Set up automated scheduling** for periodic ingestion
5. **Train team** on manual linking process
6. **Monitor and optimize** query performance


