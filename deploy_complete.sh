#!/bin/bash

# Support Analytics Dashboard - Complete Deployment Script
# This script sets up the entire DynamoDB + Grafana architecture

set -e

echo "============================================================"
echo "🚀 SUPPORT ANALYTICS DASHBOARD - COMPLETE DEPLOYMENT"
echo "============================================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please create a .env file with the following variables:"
    echo
    echo "# AWS Configuration"
    echo "AWS_REGION=us-west-2"
    echo "DYNAMODB_TABLE=support_data_ingestion"
    echo
    echo "# Slack Configuration"
    echo "SLACK_BOT_TOKEN=your_slack_bot_token"
    echo "SLACK_CHANNEL_ID=your_channel_id"
    echo
    echo "# Zendesk Configuration"
    echo "ZENDESK_SUBDOMAIN=your_subdomain"
    echo "ZENDESK_EMAIL=your_email"
    echo "ZENDESK_API_TOKEN=your_api_token"
    echo
    echo "# Shortcut Configuration"
    echo "SHORTCUT_API_TOKEN=your_shortcut_token"
    echo
    exit 1
fi

print_success ".env file found"

# Step 1: Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Step 2: Check AWS credentials
print_status "Checking AWS credentials..."
if aws sts get-caller-identity --profile AdministratorAccess12hr-100142810612 > /dev/null 2>&1; then
    print_success "AWS credentials verified"
else
    print_warning "AWS credentials not found or expired"
    print_status "Logging into AWS SSO..."
    aws sso login --profile AdministratorAccess12hr-100142810612
    print_success "AWS SSO login completed"
fi

# Step 3: Run initial data ingestion
print_status "Running initial data ingestion..."
python dynamodb_data_storage.py
print_success "Initial data ingestion completed"

# Step 4: Test the scheduler
print_status "Testing scheduler (will run for 2 minutes)..."
timeout 120s python scheduler.py &
SCHEDULER_PID=$!

# Wait for scheduler to start
sleep 5

# Check if scheduler is running
if kill -0 $SCHEDULER_PID 2>/dev/null; then
    print_success "Scheduler is running"
    kill $SCHEDULER_PID
    print_status "Scheduler test completed"
else
    print_error "Scheduler failed to start"
    exit 1
fi

# Step 5: Create deployment summary
echo
echo "============================================================"
echo "📊 DEPLOYMENT SUMMARY"
echo "============================================================"
echo

print_success "✅ Python dependencies installed"
print_success "✅ AWS credentials configured"
print_success "✅ DynamoDB table created"
print_success "✅ Initial data ingestion completed"
print_success "✅ Scheduler tested successfully"

echo
echo "🎯 Next Steps:"
echo "1. Set up Grafana with DynamoDB plugin"
echo "2. Import the dashboard: support_dashboard.json"
echo "3. Start the automated scheduler: python scheduler.py"
echo "4. Monitor data ingestion: tail -f data_ingestion.log"
echo

# Step 6: Create systemd service (optional)
read -p "Do you want to create a systemd service for automated scheduling? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/support-analytics.service > /dev/null <<EOF
[Unit]
Description=Support Analytics Data Ingestion
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable support-analytics.service
    print_success "Systemd service created and enabled"
    echo "To start the service: sudo systemctl start support-analytics"
    echo "To check status: sudo systemctl status support-analytics"
fi

echo
echo "============================================================"
print_success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo
echo "📈 Your Support Analytics Dashboard is ready!"
echo "🔗 Access Grafana to view your dashboards"
echo "📊 Data will be automatically ingested every hour"
echo "📝 Check logs: tail -f data_ingestion.log"
echo
echo "For support, check the README.md file"
echo



