# Unified BugTracker Dashboard

A modern, real-time dashboard for visualizing bug data across Slack, Shortcut, and Zendesk using the unified DynamoDB schema.

## 🎯 Features

- **Real-time Data**: Connects directly to DynamoDB `BugTracker-dev` table
- **Unified View**: Shows bugs from all three sources (Slack, Shortcut, Zendesk)
- **Interactive Charts**: Pie charts and bar charts for data visualization
- **Advanced Filtering**: Filter by source system, priority, state, and search text
- **Responsive Design**: Works on desktop and mobile devices
- **Auto-refresh**: Updates every 30 seconds automatically
- **Modern UI**: Beautiful, modern interface with smooth animations

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   DynamoDB      │
│   (HTML/JS)     │◄──►│   (Node.js)     │◄──►│   BugTracker-dev│
│                 │    │                 │    │                 │
│ - Bootstrap     │    │ - Express       │    │ - Unified Schema│
│ - Chart.js      │    │ - AWS SDK       │    │ - GSIs           │
│ - Font Awesome  │    │ - CORS          │    │ - Real-time Data │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Node.js 14+ and npm
- AWS CLI configured with SSO
- Access to `BugTracker-dev` DynamoDB table

### Installation

1. **Navigate to dashboard directory**:
   ```bash
   cd dashboard
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your AWS configuration
   ```

4. **Start the server**:
   ```bash
   npm start
   ```

5. **Open dashboard**:
   ```
   http://localhost:3000
   ```

## 📊 Dashboard Components

### 1. Statistics Cards
- **Total Bugs**: Count of all bugs across all systems
- **Slack Messages**: Count of Slack-related bugs
- **Shortcut Stories**: Count of Shortcut-related bugs  
- **Zendesk Tickets**: Count of Zendesk-related bugs

### 2. Interactive Charts
- **Bugs by Source System**: Doughnut chart showing distribution
- **Bugs by Priority**: Bar chart showing priority levels

### 3. Advanced Filters
- **Source System**: Filter by Slack, Shortcut, or Zendesk
- **Priority**: Filter by High, Medium, Low, or Unknown
- **State**: Filter by Open, Closed, In Progress, or Unknown
- **Search**: Text search across bug titles and descriptions

### 4. Bug List
- **Recent Bugs**: Latest bugs with detailed information
- **Real-time Updates**: Auto-refreshes every 30 seconds
- **Responsive Design**: Works on all screen sizes

## 🔧 API Endpoints

### GET `/api/stats`
Returns dashboard statistics:
```json
{
  "total": 75,
  "bySource": {
    "slack": 50,
    "shortcut": 25,
    "zendesk": 0
  },
  "byPriority": {
    "high": 10,
    "medium": 30,
    "low": 20,
    "unknown": 15
  },
  "byState": {
    "open": 40,
    "closed": 20,
    "in_progress": 10,
    "unknown": 5
  }
}
```

### GET `/api/bugs`
Returns filtered bugs:
```json
{
  "bugs": [...],
  "count": 25,
  "total": 75,
  "scannedCount": 75
}
```

### GET `/api/bugs/source/:sourceSystem`
Returns bugs by source system:
```json
{
  "bugs": [...],
  "count": 50,
  "sourceSystem": "slack"
}
```

### POST `/api/bugs/search`
Search bugs with filters:
```json
{
  "query": "login issue",
  "sourceSystem": "slack",
  "priority": "high",
  "state": "open"
}
```

### GET `/api/health`
Health check endpoint:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-31T16:45:22.071Z",
  "table": "BugTracker-dev",
  "region": "us-west-2"
}
```

## 🎨 Customization

### Styling
The dashboard uses CSS custom properties for easy theming:
```css
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --warning-color: #ffc107;
  --info-color: #17a2b8;
}
```

### Charts
Charts are built with Chart.js and can be customized:
- Colors and themes
- Chart types (pie, bar, line, etc.)
- Data sources and transformations

### Filters
Add new filters by modifying the HTML and JavaScript:
```javascript
// Add new filter
document.getElementById('newFilter').addEventListener('change', filterBugs);
```

## 🚀 Deployment

### Local Development
```bash
npm run dev  # Uses nodemon for auto-reload
```

### Production Deployment
```bash
# Deploy to AWS S3
./deploy.sh aws

# Deploy locally
./deploy.sh local

# Install dependencies only
./deploy.sh install
```

### AWS Deployment
The dashboard can be deployed to AWS S3 for static hosting:
1. Creates S3 bucket
2. Configures static website hosting
3. Uploads all files
4. Provides public URL

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials Error**:
   ```bash
   aws sso login --profile AdministratorAccess12hr-100142810612
   ```

2. **Port Already in Use**:
   ```bash
   export PORT=3001
   npm start
   ```

3. **DynamoDB Connection Error**:
   - Check AWS credentials
   - Verify table name: `BugTracker-dev`
   - Check region: `us-west-2`

4. **CORS Issues**:
   - Ensure CORS is enabled in server.js
   - Check browser console for errors

### Debug Mode
Enable debug logging:
```bash
DEBUG=* npm start
```

## 📈 Performance

### Optimizations
- **Lazy Loading**: Charts load only when needed
- **Debounced Search**: Prevents excessive API calls
- **Caching**: Browser caches static assets
- **Compression**: Gzip compression for responses

### Monitoring
- **Health Checks**: `/api/health` endpoint
- **Error Logging**: Console and file logging
- **Performance Metrics**: Response time tracking

## 🔐 Security

### Best Practices
- **Environment Variables**: Store sensitive data in `.env`
- **CORS Configuration**: Restrict origins in production
- **Input Validation**: Sanitize all user inputs
- **HTTPS**: Use SSL in production

### AWS Permissions
Required DynamoDB permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-west-2:*:table/BugTracker-dev"
    }
  ]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Review AWS CloudWatch logs
- Contact the development team

---

**Happy Bug Tracking! 🐛✨**


