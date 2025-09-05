# AWS SSO Setup for Timestream Data Ingestion

## Overview
This guide will help you configure AWS SSO for the Timestream data ingestion system, providing secure access to AWS resources.

## Prerequisites
- AWS SSO enabled in your AWS account
- Access to AWS SSO portal
- Appropriate permissions for Timestream services

## Step 1: Configure AWS SSO

### 1.1 Login to AWS SSO Portal
```bash
# Open your AWS SSO portal URL
# Usually: https://your-sso-portal.awsapps.com/start
```

### 1.2 Configure AWS CLI for SSO
```bash
# Configure SSO profile
aws configure sso

# Enter the following information:
# SSO start URL: https://your-sso-portal.awsapps.com/start
# SSO Region: us-east-1 (or your preferred region)
# Account ID: Your AWS account ID
# Role name: Your SSO role name
# Profile name: timestream-ingestion
```

### 1.3 Test SSO Login
```bash
# Login using SSO
aws sso login --profile timestream-ingestion

# Test authentication
aws sts get-caller-identity --profile timestream-ingestion
```

## Step 2: Update Environment Variables

Add AWS SSO profile to your `.env` file:

```env
# AWS SSO Configuration
AWS_PROFILE=timestream-ingestion
AWS_REGION=us-east-1
```

## Step 3: Required IAM Permissions

Ensure your SSO role has these Timestream permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "timestream:CreateDatabase",
                "timestream:CreateTable",
                "timestream:WriteRecords",
                "timestream:DescribeDatabase",
                "timestream:DescribeTable",
                "timestream:Select",
                "timestream:ListDatabases",
                "timestream:ListTables"
            ],
            "Resource": "*"
        }
    ]
}
```

## Step 4: Test the System

### 4.1 Login to AWS SSO
```bash
aws sso login --profile timestream-ingestion
```

### 4.2 Test Timestream Access
```bash
python timestream_data_storage.py
```

### 4.3 Run Data Ingestion
```bash
python scheduler.py
```

## Step 5: Automated SSO Login

For automated ingestion, you may need to handle SSO token refresh:

```bash
# Check if token is valid
aws sts get-caller-identity --profile timestream-ingestion

# If expired, login again
aws sso login --profile timestream-ingestion
```

## Troubleshooting

### Common Issues:
1. **Token Expired**: Run `aws sso login --profile timestream-ingestion`
2. **Permission Denied**: Check IAM permissions for your SSO role
3. **Profile Not Found**: Verify profile name in `.env` file

### Verification Commands:
```bash
# Check current identity
aws sts get-caller-identity --profile timestream-ingestion

# List Timestream databases
aws timestream list-databases --profile timestream-ingestion

# Test Timestream write access
aws timestream describe-database --database-name support_data_ingestion --profile timestream-ingestion
```

## Next Steps
1. Configure Grafana to use AWS SSO
2. Set up automated token refresh
3. Monitor SSO session expiration
4. Configure alerts for authentication issues

