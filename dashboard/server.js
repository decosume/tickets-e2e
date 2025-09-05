const express = require('express');
const cors = require('cors');
const AWS = require('aws-sdk');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Configure AWS
AWS.config.update({
    region: process.env.AWS_REGION || 'us-west-2',
    credentials: new AWS.SharedIniFileCredentials({ profile: process.env.AWS_PROFILE || 'AdministratorAccess12hr-100142810612' })
});

const dynamodb = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = 'BugTracker-dev';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('.'));

// Get all bugs from DynamoDB
app.get('/api/bugs', async (req, res) => {
    try {
        const { sourceSystem, priority, state, limit = 50 } = req.query;
        
        let params = {
            TableName: TABLE_NAME,
            Limit: parseInt(limit)
        };

        // Add filters if provided
        if (sourceSystem) {
            params.IndexName = 'source-index';
            params.KeyConditionExpression = 'sourceSystem = :source';
            params.ExpressionAttributeValues = { ':source': sourceSystem };
        }

        if (priority) {
            params.IndexName = 'priority-index';
            params.KeyConditionExpression = 'priority = :priority';
            params.ExpressionAttributeValues = { ':priority': priority };
        }

        if (state) {
            params.IndexName = 'state-index';
            params.KeyConditionExpression = 'state = :state';
            params.ExpressionAttributeValues = { ':state': state };
        }

        const result = await dynamodb.scan(params).promise();
        
        // Transform data for frontend
        const bugs = result.Items.map(item => ({
            id: item.PK,
            sourceSystem: item.sourceSystem,
            priority: item.priority || 'Unknown',
            state: item.state || 'Unknown',
            createdAt: item.createdAt,
            updatedAt: item.updatedAt,
            // Source-specific fields
            name: item.name || item.text || 'No title',
            description: item.description || item.text || 'No description',
            author: item.author || 'Unknown',
            shortcut_story_id: item.shortcut_story_id,
            completed: item.completed,
            archived: item.archived
        }));

        res.json({ 
            bugs,
            count: bugs.length,
            total: result.Count,
            scannedCount: result.ScannedCount
        });

    } catch (error) {
        console.error('Error fetching bugs:', error);
        res.status(500).json({ error: 'Failed to fetch bugs from DynamoDB' });
    }
});

// Get bugs by source system
app.get('/api/bugs/source/:sourceSystem', async (req, res) => {
    try {
        const { sourceSystem } = req.params;
        const { limit = 50 } = req.query;

        const params = {
            TableName: TABLE_NAME,
            IndexName: 'source-index',
            KeyConditionExpression: 'sourceSystem = :source',
            ExpressionAttributeValues: { ':source': sourceSystem },
            Limit: parseInt(limit),
            ScanIndexForward: false // Most recent first
        };

        const result = await dynamodb.query(params).promise();
        
        const bugs = result.Items.map(item => ({
            id: item.PK,
            sourceSystem: item.sourceSystem,
            priority: item.priority || 'Unknown',
            state: item.state || 'Unknown',
            createdAt: item.createdAt,
            updatedAt: item.updatedAt,
            name: item.name || item.text || 'No title',
            description: item.description || item.text || 'No description',
            author: item.author || 'Unknown',
            shortcut_story_id: item.shortcut_story_id,
            completed: item.completed,
            archived: item.archived
        }));

        res.json({ 
            bugs,
            count: bugs.length,
            sourceSystem
        });

    } catch (error) {
        console.error('Error fetching bugs by source:', error);
        res.status(500).json({ error: 'Failed to fetch bugs by source' });
    }
});

// Get bugs by priority
app.get('/api/bugs/priority/:priority', async (req, res) => {
    try {
        const { priority } = req.params;
        const { limit = 50 } = req.query;

        const params = {
            TableName: TABLE_NAME,
            IndexName: 'priority-index',
            KeyConditionExpression: 'priority = :priority',
            ExpressionAttributeValues: { ':priority': priority },
            Limit: parseInt(limit),
            ScanIndexForward: false
        };

        const result = await dynamodb.query(params).promise();
        
        const bugs = result.Items.map(item => ({
            id: item.PK,
            sourceSystem: item.sourceSystem,
            priority: item.priority,
            state: item.state || 'Unknown',
            createdAt: item.createdAt,
            updatedAt: item.updatedAt,
            name: item.name || item.text || 'No title',
            description: item.description || item.text || 'No description',
            author: item.author || 'Unknown',
            shortcut_story_id: item.shortcut_story_id,
            completed: item.completed,
            archived: item.archived
        }));

        res.json({ 
            bugs,
            count: bugs.length,
            priority
        });

    } catch (error) {
        console.error('Error fetching bugs by priority:', error);
        res.status(500).json({ error: 'Failed to fetch bugs by priority' });
    }
});

// Get dashboard statistics
app.get('/api/stats', async (req, res) => {
    try {
        // Get total count
        const totalResult = await dynamodb.scan({
            TableName: TABLE_NAME,
            Select: 'COUNT'
        }).promise();

        // Get counts by source system
        const sourceStats = await Promise.all([
            getCountBySource('slack'),
            getCountBySource('shortcut'),
            getCountBySource('zendesk')
        ]);

        // Get counts by priority
        const priorityStats = await Promise.all([
            getCountByPriority('high'),
            getCountByPriority('medium'),
            getCountByPriority('low'),
            getCountByPriority('Unknown')
        ]);

        // Get counts by state
        const stateStats = await Promise.all([
            getCountByState('open'),
            getCountByState('closed'),
            getCountByState('in_progress'),
            getCountByState('Unknown')
        ]);

        res.json({
            total: totalResult.Count,
            bySource: {
                slack: sourceStats[0],
                shortcut: sourceStats[1],
                zendesk: sourceStats[2]
            },
            byPriority: {
                high: priorityStats[0],
                medium: priorityStats[1],
                low: priorityStats[2],
                unknown: priorityStats[3]
            },
            byState: {
                open: stateStats[0],
                closed: stateStats[1],
                in_progress: stateStats[2],
                unknown: stateStats[3]
            }
        });

    } catch (error) {
        console.error('Error fetching stats:', error);
        res.status(500).json({ error: 'Failed to fetch statistics' });
    }
});

// Helper function to get count by source
async function getCountBySource(sourceSystem) {
    try {
        const result = await dynamodb.query({
            TableName: TABLE_NAME,
            IndexName: 'source-index',
            KeyConditionExpression: 'sourceSystem = :source',
            ExpressionAttributeValues: { ':source': sourceSystem },
            Select: 'COUNT'
        }).promise();
        return result.Count;
    } catch (error) {
        console.error(`Error getting count for ${sourceSystem}:`, error);
        return 0;
    }
}

// Helper function to get count by priority
async function getCountByPriority(priority) {
    try {
        const result = await dynamodb.query({
            TableName: TABLE_NAME,
            IndexName: 'priority-index',
            KeyConditionExpression: 'priority = :priority',
            ExpressionAttributeValues: { ':priority': priority },
            Select: 'COUNT'
        }).promise();
        return result.Count;
    } catch (error) {
        console.error(`Error getting count for priority ${priority}:`, error);
        return 0;
    }
}

// Helper function to get count by state
async function getCountByState(state) {
    try {
        const result = await dynamodb.query({
            TableName: TABLE_NAME,
            IndexName: 'state-index',
            KeyConditionExpression: 'state = :state',
            ExpressionAttributeValues: { ':state': state },
            Select: 'COUNT'
        }).promise();
        return result.Count;
    } catch (error) {
        console.error(`Error getting count for state ${state}:`, error);
        return 0;
    }
}

// Search bugs
app.post('/api/bugs/search', async (req, res) => {
    try {
        const { query, sourceSystem, priority, state, limit = 50 } = req.body;
        
        let params = {
            TableName: TABLE_NAME,
            Limit: parseInt(limit)
        };

        // Build filter expression
        let filterExpressions = [];
        let expressionAttributeValues = {};

        if (query) {
            filterExpressions.push('contains(#name, :query) OR contains(#desc, :query)');
            expressionAttributeValues[':query'] = query;
            params.ExpressionAttributeNames = {
                '#name': 'name',
                '#desc': 'description'
            };
        }

        if (sourceSystem) {
            filterExpressions.push('sourceSystem = :source');
            expressionAttributeValues[':source'] = sourceSystem;
        }

        if (priority) {
            filterExpressions.push('priority = :priority');
            expressionAttributeValues[':priority'] = priority;
        }

        if (state) {
            filterExpressions.push('state = :state');
            expressionAttributeValues[':state'] = state;
        }

        if (filterExpressions.length > 0) {
            params.FilterExpression = filterExpressions.join(' AND ');
            params.ExpressionAttributeValues = expressionAttributeValues;
        }

        const result = await dynamodb.scan(params).promise();
        
        const bugs = result.Items.map(item => ({
            id: item.PK,
            sourceSystem: item.sourceSystem,
            priority: item.priority || 'Unknown',
            state: item.state || 'Unknown',
            createdAt: item.createdAt,
            updatedAt: item.updatedAt,
            name: item.name || item.text || 'No title',
            description: item.description || item.text || 'No description',
            author: item.author || 'Unknown',
            shortcut_story_id: item.shortcut_story_id,
            completed: item.completed,
            archived: item.archived
        }));

        res.json({ 
            bugs,
            count: bugs.length,
            query,
            filters: { sourceSystem, priority, state }
        });

    } catch (error) {
        console.error('Error searching bugs:', error);
        res.status(500).json({ error: 'Failed to search bugs' });
    }
});

// Health check
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy',
        timestamp: new Date().toISOString(),
        table: TABLE_NAME,
        region: AWS.config.region
    });
});

app.listen(PORT, () => {
    console.log(`BugTracker Dashboard Server running on port ${PORT}`);
    console.log(`Connected to DynamoDB table: ${TABLE_NAME}`);
    console.log(`AWS Region: ${AWS.config.region}`);
});


