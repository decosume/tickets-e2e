const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('.'));

// Shortcut API endpoint
app.post('/api/shortcut-bugs', async (req, res) => {
    try {
        const { query, startDate, endDate } = req.body;
        
        // Get Shortcut API token from environment
        const SHORTCUT_API_TOKEN = process.env.SHORTCUT_API_TOKEN;
        
        if (!SHORTCUT_API_TOKEN) {
            return res.status(500).json({ error: 'Shortcut API token not configured' });
        }

        // Build the full query
        let fullQuery = query;
        if (startDate && endDate) {
            fullQuery += ` created:>${startDate} created:<${endDate}`;
        }

        // Make request to Shortcut API
        const response = await fetch('https://api.app.shortcut.com/api/v3/search/stories', {
            method: 'GET',
            headers: {
                'Shortcut-Token': SHORTCUT_API_TOKEN,
                'Content-Type': 'application/json'
            },
            params: {
                query: fullQuery,
                page_size: 25
            }
        });

        if (!response.ok) {
            throw new Error(`Shortcut API error: ${response.status}`);
        }

        const data = await response.json();
        const bugs = data.data || [];

        // Transform the bugs to match our expected format
        const transformedBugs = bugs.map(bug => ({
            id: bug.id,
            name: bug.name,
            description: bug.description || 'No description available',
            status: getStatusName(bug.workflow_state_id),
            assignee: getAssigneeName(bug.owner_ids),
            severity: getSeverityFromLabels(bug.labels),
            created_at: bug.created_at,
            updated_at: bug.updated_at
        }));

        res.json({ bugs: transformedBugs });

    } catch (error) {
        console.error('Error fetching bugs:', error);
        res.status(500).json({ error: 'Failed to fetch bugs from Shortcut API' });
    }
});

// Helper functions
function getStatusName(workflowStateId) {
    const statusMap = {
        "500000027": "Ready for Dev",
        "500000043": "In Progress", 
        "500000385": "Code Review",
        "500003719": "Ready for QA",
        "500009065": "Blocked",
        "500000026": "Complete",
        "500008605": "Ready for Release",
        "500000028": "Released",
        "500000042": "Ready for Tech Design Review",
        "500012452": "Ready for TDR / Sprint Assignment",
        "500000611": "Rejected",
        "500009066": "Abandoned",
        "500002973": "Backlog",
        "500006943": "Backlog (Bugs)",
        "500012485": "Backlog Refinement",
        "500012489": "3rd Refinement",
        "500000063": "1st Refinement"
    };
    return statusMap[workflowStateId] || `Unknown (${workflowStateId})`;
}

function getAssigneeName(ownerIds) {
    if (!ownerIds || ownerIds.length === 0) {
        return 'Unassigned';
    }
    if (ownerIds.length > 1) {
        return 'Multiple Assignees';
    }
    // For individual assignees, we'd need to fetch user details
    // For now, return a generic name
    return 'Assigned';
}

function getSeverityFromLabels(labels) {
    if (!labels || labels.length === 0) {
        return 'Not set';
    }
    
    const severityLabels = ['critical', 'high', 'medium', 'low'];
    for (const label of labels) {
        if (severityLabels.includes(label.name.toLowerCase())) {
            return label.name.charAt(0).toUpperCase() + label.name.slice(1);
        }
    }
    return 'Not set';
}

// Start server
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Dashboard available at: http://localhost:${PORT}`);
});



