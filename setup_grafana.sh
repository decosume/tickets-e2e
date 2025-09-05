#!/bin/bash

# Grafana Setup Script for Support Data Analytics Dashboard
# This script helps you set up Grafana with DynamoDB data source

echo "=========================================="
echo "🕒 GRAFANA SETUP FOR SUPPORT ANALYTICS"
echo "=========================================="
echo ""

# Check if Grafana is installed
if ! command -v grafana-server &> /dev/null; then
    echo "❌ Grafana is not installed."
    echo "Please install Grafana first:"
    echo "  - For Ubuntu/Debian: sudo apt-get install grafana"
    echo "  - For macOS: brew install grafana"
    echo "  - Or download from: https://grafana.com/grafana/download"
    exit 1
fi

echo "✅ Grafana is installed"

# Check if DynamoDB plugin is available
echo ""
echo "📦 Installing DynamoDB plugin..."
if command -v grafana-cli &> /dev/null; then
    grafana-cli plugins install grafana-dynamodb-datasource
    echo "✅ DynamoDB plugin installed"
else
    echo "⚠️  grafana-cli not found. Please install the DynamoDB plugin manually:"
    echo "  1. Go to Grafana UI"
    echo "  2. Configuration → Plugins"
    echo "  3. Search for 'DynamoDB'"
    echo "  4. Click Install"
fi

echo ""
echo "🔧 Configuration Steps:"
echo "========================"
echo ""
echo "1. Start Grafana:"
echo "   sudo systemctl start grafana-server"
echo "   # or: grafana-server"
echo ""
echo "2. Open Grafana in your browser:"
echo "   http://localhost:3000"
echo "   Default credentials: admin/admin"
echo ""
echo "3. Add DynamoDB Data Source:"
echo "   - Go to Configuration → Data Sources"
echo "   - Click 'Add data source'"
echo "   - Search for 'DynamoDB'"
echo "   - Configure with:"
echo "     * Name: DynamoDB Support Data"
echo "     * Region: us-west-2"
echo "     * Table: support_data_ingestion"
echo "     * Access Key: Your AWS access key"
echo "     * Secret Key: Your AWS secret key"
echo ""
echo "4. Import Dashboard:"
echo "   - Go to Dashboards → Import"
echo "   - Upload the file: support_dashboard.json"
echo "   - Select your DynamoDB data source"
echo "   - Click Import"
echo ""
echo "5. Test Data Connection:"
echo "   - Go to your dashboard"
echo "   - Check if data is loading"
echo "   - Verify all panels are working"
echo ""

# Check if AWS credentials are configured
echo "🔍 Checking AWS Configuration..."
if aws sts get-caller-identity --profile AdministratorAccess12hr-100142810612 &> /dev/null; then
    echo "✅ AWS credentials are configured"
    echo "   Profile: AdministratorAccess12hr-100142810612"
    echo "   Region: us-west-2"
else
    echo "❌ AWS credentials not found"
    echo "   Please run: aws sso login --profile AdministratorAccess12hr-100142810612"
fi

echo ""
echo "📊 Available Data in DynamoDB:"
echo "==============================="
aws dynamodb scan --table-name support_data_ingestion --select COUNT --profile AdministratorAccess12hr-100142810612 2>/dev/null || echo "   Table not accessible or empty"

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "1. Start Grafana server"
echo "2. Configure DynamoDB data source"
echo "3. Import the dashboard"
echo "4. Set up automated data ingestion:"
echo "   python scheduler.py"
echo ""
echo "📚 Documentation:"
echo "================="
echo "- Setup Guide: grafana_dynamodb_setup.md"
echo "- Dashboard JSON: support_dashboard.json"
echo "- Data Ingestion: dynamodb_data_storage.py"
echo ""

echo "🚀 Ready to visualize your support data!"

