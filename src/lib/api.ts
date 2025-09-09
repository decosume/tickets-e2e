import AWS from 'aws-sdk';

// Configure AWS
AWS.config.update({
  region: process.env.NEXT_PUBLIC_AWS_REGION || 'us-west-2',
  credentials: new AWS.SharedIniFileCredentials({ 
    profile: process.env.NEXT_PUBLIC_AWS_PROFILE || 'AdministratorAccess12hr-100142810612' 
  })
});

const dynamodb = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = 'BugTracker-dev';

export interface Bug {
  id: string;
  sourceSystem: string;
  priority: string;
  state: string;
  name: string;
  description?: string;
  author?: string;
  createdAt: string;
  updatedAt: string;
}

export interface DashboardStats {
  total: number;
  bySource: {
    slack: number;
    shortcut: number;
    zendesk: number;
  };
  byPriority: {
    high: number;
    medium: number;
    low: number;
    unknown: number;
  };
  byState: {
    open: number;
    closed: number;
    in_progress: number;
    unknown: number;
  };
}

export interface BugFilters {
  sourceSystem?: string;
  priority?: string;
  state?: string;
  search?: string;
}

class BugTrackerAPI {
  // Get dashboard statistics
  async getStats(): Promise<DashboardStats> {
    try {
      // Get total count
      const totalResult = await dynamodb.scan({
        TableName: TABLE_NAME,
        Select: 'COUNT'
      }).promise();

      // Get counts by source system
      const sourceStats = await Promise.all([
        this.getCountBySource('slack'),
        this.getCountBySource('shortcut'),
        this.getCountBySource('zendesk')
      ]);

      // Get counts by priority
      const priorityStats = await Promise.all([
        this.getCountByPriority('high'),
        this.getCountByPriority('medium'),
        this.getCountByPriority('low'),
        this.getCountByPriority('Unknown')
      ]);

      // Get counts by state
      const stateStats = await Promise.all([
        this.getCountByState('open'),
        this.getCountByState('closed'),
        this.getCountByState('in_progress'),
        this.getCountByState('Unknown')
      ]);

      return {
        total: totalResult.Count || 0,
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
      };
    } catch (error) {
      console.error('Error fetching stats:', error);
      throw new Error('Failed to fetch statistics');
    }
  }

  // Get bugs with filters
  async getBugs(filters: BugFilters = {}, limit: number = 50): Promise<Bug[]> {
    try {
      let params: any = {
        TableName: TABLE_NAME,
        Limit: limit
      };

      // Add filters if provided
      if (filters.sourceSystem) {
        params.IndexName = 'source-index';
        params.KeyConditionExpression = 'sourceSystem = :source';
        params.ExpressionAttributeValues = { ':source': filters.sourceSystem };
      }

      if (filters.priority) {
        params.IndexName = 'priority-index';
        params.KeyConditionExpression = 'priority = :priority';
        params.ExpressionAttributeValues = { ':priority': filters.priority };
      }

      if (filters.state) {
        params.IndexName = 'state-index';
        params.KeyConditionExpression = 'state = :state';
        params.ExpressionAttributeValues = { ':state': filters.state };
      }

      const result = await dynamodb.scan(params).promise();
      
      // Transform data for frontend
      const bugs = (result.Items || []).map((item: any) => ({
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

      // Apply search filter if provided
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase();
        return bugs.filter(bug => 
          bug.name.toLowerCase().includes(searchTerm) ||
          bug.description.toLowerCase().includes(searchTerm)
        );
      }

      return bugs;
    } catch (error) {
      console.error('Error fetching bugs:', error);
      throw new Error('Failed to fetch bugs');
    }
  }

  // Helper function to get count by source
  private async getCountBySource(sourceSystem: string): Promise<number> {
    try {
      const result = await dynamodb.query({
        TableName: TABLE_NAME,
        IndexName: 'source-index',
        KeyConditionExpression: 'sourceSystem = :source',
        ExpressionAttributeValues: { ':source': sourceSystem },
        Select: 'COUNT'
      }).promise();
      return result.Count || 0;
    } catch (error) {
      console.error(`Error getting count for ${sourceSystem}:`, error);
      return 0;
    }
  }

  // Helper function to get count by priority
  private async getCountByPriority(priority: string): Promise<number> {
    try {
      const result = await dynamodb.query({
        TableName: TABLE_NAME,
        IndexName: 'priority-index',
        KeyConditionExpression: 'priority = :priority',
        ExpressionAttributeValues: { ':priority': priority },
        Select: 'COUNT'
      }).promise();
      return result.Count || 0;
    } catch (error) {
      console.error(`Error getting count for priority ${priority}:`, error);
      return 0;
    }
  }

  // Helper function to get count by state
  private async getCountByState(state: string): Promise<number> {
    try {
      const result = await dynamodb.query({
        TableName: TABLE_NAME,
        IndexName: 'state-index',
        KeyConditionExpression: 'state = :state',
        ExpressionAttributeValues: { ':state': state },
        Select: 'COUNT'
      }).promise();
      return result.Count || 0;
    } catch (error) {
      console.error(`Error getting count for state ${state}:`, error);
      return 0;
    }
  }
}

export const bugTrackerAPI = new BugTrackerAPI();


