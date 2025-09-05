# Grafana Dashboard Setup Guide for Timestream Data

## Overview
This guide will help you set up Grafana to visualize data from AWS Timestream, which contains support data from Slack, Zendesk, and Shortcut.

## Prerequisites
- AWS account with Timestream access
- Grafana instance (cloud or self-hosted)
- Data already ingested into Timestream

## Step 1: Install Timestream Plugin for Grafana

### Option A: Grafana Cloud
1. Go to your Grafana Cloud instance
2. Navigate to **Configuration** → **Plugins**
3. Search for "Amazon Timestream"
4. Click **Install**

### Option B: Self-hosted Grafana
```bash
# Install the plugin
grafana-cli plugins install grafana-timestream-datasource

# Restart Grafana
sudo systemctl restart grafana-server
```

## Step 2: Configure Timestream Data Source

1. In Grafana, go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Search for **Amazon Timestream**
4. Configure with your AWS credentials:
   - **Name**: `Timestream Support Data`
   - **Region**: `us-east-1`
   - **Database**: `support_data_ingestion`
   - **Table**: `support_metrics`
   - **Access Key ID**: Your AWS access key
   - **Secret Access Key**: Your AWS secret key

## Step 3: Create Dashboard Panels

### Panel 1: Support Ticket Overview
**Query:**
```sql
SELECT 
    data_type,
    COUNT(*) as count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'zendesk_ticket'
    AND time >= now() - 30d
GROUP BY data_type
```

**Visualization**: Stat panel
**Title**: Total Support Tickets (30 days)

### Panel 2: Ticket Status Distribution
**Query:**
```sql
SELECT 
    status,
    COUNT(*) as count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'zendesk_ticket'
    AND time >= now() - 30d
GROUP BY status
ORDER BY count DESC
```

**Visualization**: Pie chart
**Title**: Ticket Status Distribution

### Panel 3: Slack Activity Timeline
**Query:**
```sql
SELECT 
    time,
    COUNT(*) as message_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'slack_message'
    AND time >= now() - 7d
GROUP BY time
ORDER BY time
```

**Visualization**: Time series
**Title**: Slack Messages (7 days)

### Panel 4: Project Progress (Shortcut Epics)
**Query:**
```sql
SELECT 
    state,
    COUNT(*) as count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'shortcut_epic'
GROUP BY state
```

**Visualization**: Bar chart
**Title**: Epic Status Distribution

### Panel 5: Support Response Time
**Query:**
```sql
SELECT 
    priority,
    COUNT(*) as ticket_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'zendesk_ticket'
    AND time >= now() - 30d
GROUP BY priority
```

**Visualization**: Bar chart
**Title**: Tickets by Priority

## Step 4: Create Dashboard Variables

### Variable 1: Time Range
- **Name**: `timeRange`
- **Type**: Query
- **Query**: `SELECT '30d' as value UNION SELECT '7d' UNION SELECT '24h'`

### Variable 2: Data Source
- **Name**: `dataSource`
- **Type**: Query
- **Query**: `SELECT 'slack_message' as value UNION SELECT 'zendesk_ticket' UNION SELECT 'shortcut_epic'`

## Step 5: Advanced Queries

### Real-time Support Metrics
```sql
SELECT 
    data_type,
    COUNT(*) as count,
    time
FROM "support_data_ingestion"."support_metrics"
WHERE time >= now() - 1h
GROUP BY data_type, time
ORDER BY time
```

### User Activity Analysis
```sql
SELECT 
    user_id,
    COUNT(*) as message_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'slack_message'
    AND time >= now() - 7d
GROUP BY user_id
ORDER BY message_count DESC
LIMIT 10
```

### Project Velocity
```sql
SELECT 
    name,
    state,
    COUNT(*) as epic_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'shortcut_epic'
GROUP BY name, state
ORDER BY epic_count DESC
```

## Step 6: Dashboard Layout

### Row 1: Overview Metrics
- Total Tickets (Stat)
- Active Epics (Stat)
- Slack Messages Today (Stat)
- Response Time Avg (Stat)

### Row 2: Support Analysis
- Ticket Status Distribution (Pie)
- Priority Breakdown (Bar)
- Tickets Over Time (Time series)

### Row 3: Communication
- Slack Activity Timeline (Time series)
- User Activity Heatmap (Heatmap)
- Message Types (Pie)

### Row 4: Project Management
- Epic Status Distribution (Bar)
- Iteration Progress (Gauge)
- Project Velocity (Bar)

## Step 7: Alerts and Notifications

### Alert 1: High Priority Tickets
```sql
SELECT COUNT(*) as high_priority_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'zendesk_ticket'
    AND priority = 'urgent'
    AND time >= now() - 1h
```

**Condition**: `high_priority_count > 5`

### Alert 2: No Slack Activity
```sql
SELECT COUNT(*) as message_count
FROM "support_data_ingestion"."support_metrics"
WHERE data_type = 'slack_message'
    AND time >= now() - 2h
```

**Condition**: `message_count = 0`

## Step 8: Export Dashboard

1. Go to your dashboard
2. Click **Settings** → **JSON Model**
3. Copy the JSON
4. Save as `support_dashboard.json`

## Troubleshooting

### Common Issues:
1. **No data showing**: Check AWS credentials and Timestream permissions
2. **Slow queries**: Add time filters to reduce data scanned
3. **Authentication errors**: Verify IAM roles and policies

### IAM Permissions Required:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "timestream:DescribeDatabase",
                "timestream:DescribeTable",
                "timestream:Select"
            ],
            "Resource": "*"
        }
    ]
}
```

## Next Steps
1. Set up automated data ingestion scheduling
2. Create additional dashboards for specific teams
3. Configure alerts for critical metrics
4. Set up data retention policies

