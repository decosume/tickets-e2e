# Grafana Dashboard Setup for BugTracker DynamoDB Data

## Overview
This guide will help you set up Grafana to visualize unified bug tracking data from DynamoDB, including Slack messages, Zendesk tickets, and Shortcut project data using the new unified schema.

## Prerequisites
- Grafana instance (cloud or self-hosted)
- AWS DynamoDB table: `BugTracker-dev`
- AWS credentials configured

## Step 1: Install DynamoDB Plugin for Grafana

### Option A: Grafana Cloud
1. Go to your Grafana Cloud instance
2. Navigate to **Configuration** → **Plugins**
3. Search for "DynamoDB" or "AWS DynamoDB"
4. Click **Install**

### Option B: Self-hosted Grafana
```bash
# Install the plugin
grafana-cli plugins install grafana-dynamodb-datasource

# Restart Grafana
sudo systemctl restart grafana-server
```

## Step 2: Configure DynamoDB Data Source

1. In Grafana, go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Search for **DynamoDB** or **AWS DynamoDB**
4. Configure with your AWS credentials:
   - **Name**: `DynamoDB BugTracker`
   - **Region**: `us-west-2`
   - **Table**: `BugTracker-dev`
   - **Access Key ID**: Your AWS access key
   - **Secret Access Key**: Your AWS secret key
   - **Profile**: `AdministratorAccess12hr-100142810612`

## Step 3: Import the Dashboard

1. Go to **Dashboards** → **Import**
2. Upload the `support_dashboard.json` file
3. Select the `DynamoDB BugTracker` data source
4. Click **Import**

## Step 4: Dashboard Panels

### Panel 1: Total Bugs Overview
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "Select": "COUNT"
}
```

**Visualization**: Stat panel
**Title**: Total Bugs Across All Systems

### Panel 2: Bugs by Source System
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "source-index",
  "ProjectionExpression": "sourceSystem",
  "Select": "COUNT"
}
```

**Visualization**: Pie chart
**Title**: Bugs by Source System

### Panel 3: Slack Messages Count
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "source-index",
  "KeyConditionExpression": "sourceSystem = :source",
  "ExpressionAttributeValues": {
    ":source": "slack"
  },
  "Select": "COUNT"
}
```

**Visualization**: Stat panel
**Title**: Slack Messages

### Panel 4: Shortcut Stories Count
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "source-index",
  "KeyConditionExpression": "sourceSystem = :source",
  "ExpressionAttributeValues": {
    ":source": "shortcut"
  },
  "Select": "COUNT"
}
```

**Visualization**: Stat panel
**Title**: Shortcut Stories

### Panel 5: Zendesk Tickets Count
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "source-index",
  "KeyConditionExpression": "sourceSystem = :source",
  "ExpressionAttributeValues": {
    ":source": "zendesk"
  },
  "Select": "COUNT"
}
```

**Visualization**: Stat panel
**Title**: Zendesk Tickets

### Panel 6: Bugs by Priority
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "priority-index",
  "ProjectionExpression": "priority",
  "Select": "COUNT"
}
```

**Visualization**: Bar chart
**Title**: Bugs by Priority

### Panel 7: High Priority Bugs
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "priority-index",
  "KeyConditionExpression": "priority = :priority",
  "ExpressionAttributeValues": {
    ":priority": "high"
  },
  "Select": "COUNT"
}
```

**Visualization**: Stat panel with thresholds
**Title**: High Priority Bugs

### Panel 8: Bugs by State
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "IndexName": "state-index",
  "ProjectionExpression": "state",
  "Select": "COUNT"
}
```

**Visualization**: Bar chart
**Title**: Bugs by State

### Panel 9: Recent Bugs Timeline
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "ProjectionExpression": "createdAt, sourceSystem",
  "ScanIndexForward": false,
  "Limit": 100
}
```

**Visualization**: Time series
**Title**: Recent Bugs Timeline

### Panel 10: Recent Bug Details
**Query:**
```json
{
  "TableName": "BugTracker-dev",
  "ProjectionExpression": "PK, SK, sourceSystem, createdAt, priority, state",
  "ScanIndexForward": false,
  "Limit": 20
}
```

**Visualization**: Table
**Title**: Recent Bug Details

## Step 5: Template Variables

The dashboard includes template variables for filtering:

### Source System Variable
- **Name**: `source_system`
- **Query**: Uses `source-index` to get all source systems
- **Multi-select**: Enabled

### Priority Variable
- **Name**: `priority`
- **Query**: Uses `priority-index` to get all priorities
- **Multi-select**: Enabled

## Step 6: Unified Schema Understanding

The new `BugTracker-dev` table uses a unified schema:

### Key Structure
- **Primary Key (PK)**: `ticketId` (e.g., `ZD-12345`, `SC-56789`, `SL-9876543210.12345`)
- **Sort Key (SK)**: `sourceSystem#recordId` (e.g., `zendesk#12345`, `slack#9876543210.12345`)

### Global Secondary Indexes
- `source-index`: Query by source system
- `priority-index`: Query by priority
- `state-index`: Query by state

### Common Fields
- `sourceSystem`: "slack", "shortcut", "zendesk"
- `priority`: "high", "medium", "low", "Unknown"
- `state`: "open", "closed", "in_progress", "Unknown"
- `createdAt`: Creation timestamp
- `updatedAt`: Last update timestamp

## Step 7: Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify AWS credentials
   - Check IAM permissions for DynamoDB access
   - Ensure the profile is correctly configured

2. **Table Not Found**:
   - Verify table name: `BugTracker-dev`
   - Check AWS region: `us-west-2`
   - Ensure table exists and is accessible

3. **Index Errors**:
   - Verify GSI names: `source-index`, `priority-index`, `state-index`
   - Check that indexes are active and not being created

4. **Query Performance**:
   - Use appropriate indexes for queries
   - Limit scan operations
   - Use projection expressions to reduce data transfer

### Debugging Queries

Test queries directly in AWS CLI:
```bash
# Test source system query
aws dynamodb query \
  --table-name BugTracker-dev \
  --index-name source-index \
  --key-condition-expression "sourceSystem = :source" \
  --expression-attribute-values '{":source":{"S":"slack"}}' \
  --select COUNT \
  --profile AdministratorAccess12hr-100142810612 \
  --region us-west-2

# Test priority query
aws dynamodb query \
  --table-name BugTracker-dev \
  --index-name priority-index \
  --key-condition-expression "priority = :priority" \
  --expression-attribute-values '{":priority":{"S":"high"}}' \
  --select COUNT \
  --profile AdministratorAccess12hr-100142810612 \
  --region us-west-2
```

## Step 8: Monitoring and Alerts

### Set Up Alerts
1. **High Priority Bug Alert**:
   - Monitor high priority bugs count
   - Alert when count exceeds threshold

2. **Data Ingestion Alert**:
   - Monitor new bug creation rate
   - Alert if ingestion stops

3. **Error Rate Alert**:
   - Monitor query error rates
   - Alert on authentication failures

### Performance Monitoring
- Monitor query response times
- Track DynamoDB consumed capacity
- Watch for throttling events

## Step 9: Best Practices

### Query Optimization
- Use GSIs for efficient filtering
- Limit scan operations
- Use projection expressions
- Implement pagination for large datasets

### Security
- Use IAM roles with least privilege
- Enable CloudTrail logging
- Regularly rotate access keys
- Use VPC endpoints for private access

### Maintenance
- Monitor index usage
- Review and optimize queries
- Update dashboard queries as schema evolves
- Regular backup and recovery testing

## Step 10: Next Steps

1. **Customize Dashboard**: Modify panels and queries for your specific needs
2. **Add Alerts**: Set up monitoring and alerting rules
3. **Performance Tuning**: Optimize queries and indexes
4. **Integration**: Connect with other monitoring tools
5. **Documentation**: Document custom queries and configurations

---

**The unified BugTracker dashboard is now ready to provide real-time insights across all your bug tracking systems! 🐛✨**

