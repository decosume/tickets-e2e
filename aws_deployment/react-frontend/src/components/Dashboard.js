import React, { useState, useEffect } from 'react';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, ScanCommand, QueryCommand } from '@aws-sdk/lib-dynamodb';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import GrafanaDashboard from './GrafanaDashboard';
import './Dashboard.css';

const Dashboard = () => {
  const [metrics, setMetrics] = useState({
    totalTickets: 0,
    totalMessages: 0,
    totalEpics: 0,
    avgResponseTime: 0,
    ticketStatus: [],
    priorityBreakdown: [],
    slackActivity: [],
    epicStatus: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('react'); // 'react' or 'grafana'

  // Initialize DynamoDB client
  const client = new DynamoDBClient({ region: 'us-west-2' });
  const docClient = DynamoDBDocumentClient.from(client);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data from DynamoDB
      const scanCommand = new ScanCommand({
        TableName: 'support_data_ingestion',
        Limit: 1000
      });

      const response = await docClient.send(scanCommand);
      const items = response.Items || [];

      // Process data for different metrics
      const processedData = processData(items);
      setMetrics(processedData);
      
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const processData = (items) => {
    const tickets = items.filter(item => item.data_type === 'zendesk_ticket');
    const messages = items.filter(item => item.data_type === 'slack_message');
    const epics = items.filter(item => item.data_type === 'shortcut_epic');

    // Calculate metrics
    const totalTickets = tickets.length;
    const totalMessages = messages.length;
    const totalEpics = epics.length;

    // Ticket status breakdown
    const statusCount = {};
    tickets.forEach(ticket => {
      const status = ticket.status || 'Unknown';
      statusCount[status] = (statusCount[status] || 0) + 1;
    });
    const ticketStatus = Object.entries(statusCount).map(([status, count]) => ({
      name: status,
      value: count
    }));

    // Priority breakdown
    const priorityCount = {};
    tickets.forEach(ticket => {
      const priority = ticket.priority || 'Unknown';
      priorityCount[priority] = (priorityCount[priority] || 0) + 1;
    });
    const priorityBreakdown = Object.entries(priorityCount).map(([priority, count]) => ({
      name: priority,
      value: count
    }));

    // Slack activity timeline (last 7 days)
    const messageCount = {};
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    messages.forEach(message => {
      const messageDate = new Date(message.timestamp);
      if (messageDate >= sevenDaysAgo) {
        const dateKey = messageDate.toISOString().split('T')[0];
        messageCount[dateKey] = (messageCount[dateKey] || 0) + 1;
      }
    });
    const slackActivity = Object.entries(messageCount).map(([date, count]) => ({
      date,
      messages: count
    }));

    // Epic status
    const epicStatusCount = {};
    epics.forEach(epic => {
      const state = epic.state || 'Unknown';
      epicStatusCount[state] = (epicStatusCount[state] || 0) + 1;
    });
    const epicStatus = Object.entries(epicStatusCount).map(([state, count]) => ({
      name: state,
      value: count
    }));

    // Average response time
    const responseTimes = tickets
      .filter(ticket => ticket.response_time)
      .map(ticket => ticket.response_time);
    const avgResponseTime = responseTimes.length > 0 
      ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length 
      : 0;

    return {
      totalTickets,
      totalMessages,
      totalEpics,
      avgResponseTime: Math.round(avgResponseTime),
      ticketStatus,
      priorityBreakdown,
      slackActivity,
      epicStatus
    };
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  if (loading) {
    return <div className="loading">Loading dashboard data...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Support Analytics Dashboard</h1>
        <div className="view-toggle">
          <button 
            className={viewMode === 'react' ? 'active' : ''}
            onClick={() => setViewMode('react')}
          >
            React Charts
          </button>
          <button 
            className={viewMode === 'grafana' ? 'active' : ''}
            onClick={() => setViewMode('grafana')}
          >
            Grafana Dashboard
          </button>
        </div>
      </div>
      
      {viewMode === 'react' ? (
        <>
          {/* Key Metrics */}
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>Total Support Tickets</h3>
              <div className="metric-value">{metrics.totalTickets}</div>
            </div>
            <div className="metric-card">
              <h3>Slack Messages Today</h3>
              <div className="metric-value">{metrics.totalMessages}</div>
            </div>
            <div className="metric-card">
              <h3>Active Epics</h3>
              <div className="metric-value">{metrics.totalEpics}</div>
            </div>
            <div className="metric-card">
              <h3>Avg Response Time (hrs)</h3>
              <div className="metric-value">{metrics.avgResponseTime}</div>
            </div>
          </div>

          {/* Charts */}
          <div className="charts-grid">
            <div className="chart-card">
              <h3>Ticket Status Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={metrics.ticketStatus}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {metrics.ticketStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Priority Breakdown</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={metrics.priorityBreakdown}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Slack Activity (Last 7 Days)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metrics.slackActivity}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="messages" stroke="#8884d8" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Epic Status Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={metrics.epicStatus}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {metrics.epicStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      ) : (
        <GrafanaDashboard 
          dashboardId="support-analytics"
          panelId="1"
          timeRange="now-7d"
        />
      )}
    </div>
  );
};

export default Dashboard;
