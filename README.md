## Purpose
This repository contains the unified bug tracking system that integrates data from Slack, Zendesk, and Shortcut into a single DynamoDB table.

Resources included:
1. Lambda Functions (Ingestion, Query, Linker)
2. API Gateway
3. DynamoDB Table with Global Secondary Indexes

The repository follows the `casting-deployments` microservice pattern.

**Use in combination with the `casting-deployments` repository.**

## File Mapping

- `src/app.py` - Main Lambda handler following the casting pattern
- `src/castifi/controller/` - Request routing and response handling
- `src/castifi/service/` - Business logic and service orchestration
- `src/castifi/exceptions/` - Custom exception classes
- `src/castifi/repository/model/` - Data models and schemas
- `src/castifi/converter/` - Data transformation utilities
- `src/aws/` - AWS service abstractions
- `template.yaml` - SAM template for deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │   Lambda        │    │   DynamoDB      │
│   (REST API)    │◄──►│   Functions     │◄──►│   BugTracker    │
│                 │    │                 │    │                 │
│ - /query-bugs   │    │ - Ingestion     │    │ - Unified Schema│
│ - /link-bugs    │    │ - Query         │    │ - GSIs          │
│ - CORS enabled  │    │ - Linker        │    │ - Multi-source  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Data Sources

- **Slack** - Bug reports from monitored channels
- **Zendesk** - Customer support tickets
- **Shortcut** - Development tasks and bugs

## API Endpoints

- `GET /query-bugs` - Query bugs with filters (sourceSystem, priority, state)
- `POST /link-bugs` - Link related bugs across systems

## Deployment

This service is deployed using the `casting-deployments` framework:

```bash
# From casting-deployments directory
python3 cmd --env evt-bugtracker --lambdas tickets-e2e-service deploy
```

## Environment Configuration

Add to your environment YAML file:

```yaml
tickets-e2e-service:
  slackBotToken: "xoxb-your-slack-bot-token"
  slackChannelId: "C1234567890"
  zendeskSubdomain: "yourcompany"
  zendeskEmail: "api@yourcompany.com"
  zendeskApiToken: "your-zendesk-api-token"
  shortcutApiToken: "your-shortcut-api-token"
```

## Testing

```bash
# Run unit tests
python3 cmd --env evt-bugtracker --lambdas tickets-e2e-service utest

# Run integration tests
python3 cmd --env evt-bugtracker --lambdas tickets-e2e-service itest
```

## Local Development

```bash
# Start local API Gateway
python3 cmd --env evt-bugtracker --lambdas tickets-e2e-service start
```

## Monitoring

- CloudWatch Logs: `/aws/lambda/{environment}_bug-tracker-*`
- CloudWatch Alarms: High error rates and failures
- SNS Notifications: Alert on critical issues

## Database Schema

The DynamoDB table uses a unified schema:

- **PK**: Ticket ID (e.g., ZD-12345, SC-56789, SL-9876543210.12345)
- **SK**: Source system + record ID (e.g., slack#1234567890.12345)
- **GSIs**: priority-index, state-index, source-index

## Contributing

1. Follow the casting pattern architecture
2. Add tests for new functionality
3. Update documentation
4. Follow Python best practices
5. Use type hints where appropriate