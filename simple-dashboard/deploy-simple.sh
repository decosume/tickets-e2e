#!/bin/bash

# Quick Win Dashboard Deployment
# Deploy a simple HTML dashboard to S3 in minutes

set -e

echo "=========================================="
echo "🚀 QUICK WIN DASHBOARD DEPLOYMENT"
echo "=========================================="
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
echo "🔍 Checking AWS credentials..."
if aws sts get-caller-identity --profile AdministratorAccess12hr-100142810612 &> /dev/null; then
    echo "✅ AWS credentials are configured"
else
    echo "❌ AWS credentials not found"
    echo "Please run: aws sso login --profile AdministratorAccess12hr-100142810612"
    exit 1
fi

# Create S3 bucket for dashboard
BUCKET_NAME="support-analytics-dashboard-$(date +%s)"
echo ""
echo "📦 Creating S3 bucket: $BUCKET_NAME"

aws s3 mb s3://$BUCKET_NAME --region us-west-2 --profile AdministratorAccess12hr-100142810612

# Configure bucket for static website hosting
echo "🌐 Configuring static website hosting..."
aws s3 website s3://$BUCKET_NAME \
    --index-document index.html \
    --error-document index.html \
    --profile AdministratorAccess12hr-100142810612

# Set bucket policy for public read access
echo "🔓 Setting bucket policy for public access..."
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy file://bucket-policy.json \
    --profile AdministratorAccess12hr-100142810612

# Deploy dashboard files
echo "📤 Deploying dashboard files..."
aws s3 cp index.html s3://$BUCKET_NAME/ \
    --profile AdministratorAccess12hr-100142810612

# Get the website URL
WEBSITE_URL=$(aws s3api get-bucket-website \
    --bucket $BUCKET_NAME \
    --profile AdministratorAccess12hr-100142810612 \
    --query 'WebsiteConfiguration.IndexDocument.Suffix' \
    --output text)

echo ""
echo "🎉 Dashboard deployed successfully!"
echo ""
echo "📊 Dashboard URL:"
echo "http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com"
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Visit the dashboard URL above"
echo "2. Share with your team"
echo "3. Customize the data source to connect to your DynamoDB"
echo ""
echo "💰 Cost: ~$0.50/month for S3 hosting"
echo ""
echo "🔧 To update the dashboard:"
echo "aws s3 cp index.html s3://$BUCKET_NAME/ --profile AdministratorAccess12hr-100142810612"
echo ""
echo "🗑️  To clean up:"
echo "aws s3 rb s3://$BUCKET_NAME --force --profile AdministratorAccess12hr-100142810612"

# Clean up temporary files
rm -f bucket-policy.json

echo ""
echo "🚀 Your quick win dashboard is live!"



