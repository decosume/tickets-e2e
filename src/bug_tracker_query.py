import os
import boto3
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'BugTracker')
table = dynamodb.Table(table_name)


class BugTrackerQuery:
    def __init__(self):
        self.table = table
    
    def get_bugs_by_ticket_id(self, ticket_id):
        """Get all records for a specific ticket ID"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :ticket_id',
                ExpressionAttributeValues={
                    ':ticket_id': ticket_id
                }
            )
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': response.get('Items', [])
            }
        except Exception as e:
            logger.error(f"Error querying by ticket ID: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'items': []
            }
    
    def get_bugs_by_priority(self, priority, time_range=None):
        """Get all bugs by priority using GSI"""
        try:
            key_condition = 'priority = :priority'
            expression_values = {':priority': priority}
            
            if time_range:
                # Add time range filter if provided
                start_date = time_range.get('start_date')
                end_date = time_range.get('end_date')
                
                if start_date and end_date:
                    key_condition += ' AND createdAt BETWEEN :start_date AND :end_date'
                    expression_values[':start_date'] = start_date
                    expression_values[':end_date'] = end_date
            
            response = self.table.query(
                IndexName='priority-index',
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': response.get('Items', []),
                'priority': priority
            }
        except Exception as e:
            logger.error(f"Error querying by priority: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'items': []
            }
    
    def get_bugs_by_state(self, state, time_range=None):
        """Get all bugs by state using GSI"""
        try:
            key_condition = 'state = :state'
            expression_values = {':state': state}
            
            if time_range:
                # Add time range filter if provided
                start_date = time_range.get('start_date')
                end_date = time_range.get('end_date')
                
                if start_date and end_date:
                    key_condition += ' AND createdAt BETWEEN :start_date AND :end_date'
                    expression_values[':start_date'] = start_date
                    expression_values[':end_date'] = end_date
            
            response = self.table.query(
                IndexName='state-index',
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': response.get('Items', []),
                'state': state
            }
        except Exception as e:
            logger.error(f"Error querying by state: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'items': []
            }
    
    def get_bugs_by_source(self, source_system, time_range=None):
        """Get all bugs by source system using GSI"""
        try:
            key_condition = 'sourceSystem = :source_system'
            expression_values = {':source_system': source_system}
            
            if time_range:
                # Add time range filter if provided
                start_date = time_range.get('start_date')
                end_date = time_range.get('end_date')
                
                if start_date and end_date:
                    key_condition += ' AND createdAt BETWEEN :start_date AND :end_date'
                    expression_values[':start_date'] = start_date
                    expression_values[':end_date'] = end_date
            
            response = self.table.query(
                IndexName='source-index',
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': response.get('Items', []),
                'source_system': source_system
            }
        except Exception as e:
            logger.error(f"Error querying by source: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'items': []
            }
    
    def get_bugs_summary(self, time_range=None):
        """Get summary statistics for all bugs"""
        try:
            # Get counts by priority
            priorities = ['High', 'Medium', 'Low', 'Critical', 'Unknown']
            priority_counts = {}
            
            for priority in priorities:
                result = self.get_bugs_by_priority(priority, time_range)
                if result['success']:
                    priority_counts[priority] = result['count']
                else:
                    priority_counts[priority] = 0
            
            # Get counts by state
            states = ['open', 'closed', 'pending', 'Ready for Dev', 'In Progress', 'Ready for QA', 'Blocked']
            state_counts = {}
            
            for state in states:
                result = self.get_bugs_by_state(state, time_range)
                if result['success']:
                    state_counts[state] = result['count']
                else:
                    state_counts[state] = 0
            
            # Get counts by source
            sources = ['slack', 'zendesk', 'shortcut']
            source_counts = {}
            
            for source in sources:
                result = self.get_bugs_by_source(source, time_range)
                if result['success']:
                    source_counts[source] = result['count']
                else:
                    source_counts[source] = 0
            
            # Calculate total bugs
            total_bugs = sum(priority_counts.values())
            
            return {
                'success': True,
                'summary': {
                    'total_bugs': total_bugs,
                    'by_priority': priority_counts,
                    'by_state': state_counts,
                    'by_source': source_counts,
                    'time_range': time_range
                }
            }
        except Exception as e:
            logger.error(f"Error getting bugs summary: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_time_series_data(self, days=7):
        """Get time series data of new bugs over time"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for DynamoDB query
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            # Query all bugs in the time range
            response = self.table.scan(
                FilterExpression='createdAt BETWEEN :start_date AND :end_date',
                ExpressionAttributeValues={
                    ':start_date': start_date_str,
                    ':end_date': end_date_str
                }
            )
            
            # Group by date
            bugs_by_date = {}
            for item in response.get('Items', []):
                created_at = item.get('createdAt', '')
                if created_at:
                    # Extract date part
                    date_part = created_at.split('T')[0]
                    if date_part not in bugs_by_date:
                        bugs_by_date[date_part] = 0
                    bugs_by_date[date_part] += 1
            
            # Convert to time series format
            time_series = []
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                count = bugs_by_date.get(date_str, 0)
                time_series.append({
                    'date': date_str,
                    'count': count
                })
                current_date += timedelta(days=1)
            
            return {
                'success': True,
                'time_series': time_series,
                'total_days': days
            }
        except Exception as e:
            logger.error(f"Error getting time series data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def lambda_handler(event, context):
    """
    Lambda handler for BugTracker query operations
    """
    try:
        # Parse the request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        query_type = body.get('query_type', '')
        query_params = body.get('params', {})
        time_range = body.get('time_range')
        
        query = BugTrackerQuery()
        
        if query_type == 'by_ticket_id':
            ticket_id = query_params.get('ticket_id')
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: ticket_id'
                    })
                }
            result = query.get_bugs_by_ticket_id(ticket_id)
            
        elif query_type == 'by_priority':
            priority = query_params.get('priority')
            if not priority:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: priority'
                    })
                }
            result = query.get_bugs_by_priority(priority, time_range)
            
        elif query_type == 'by_state':
            state = query_params.get('state')
            if not state:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: state'
                    })
                }
            result = query.get_bugs_by_state(state, time_range)
            
        elif query_type == 'by_source':
            source_system = query_params.get('source_system')
            if not source_system:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: source_system'
                    })
                }
            result = query.get_bugs_by_source(source_system, time_range)
            
        elif query_type == 'summary':
            result = query.get_bugs_summary(time_range)
            
        elif query_type == 'time_series':
            days = query_params.get('days', 7)
            result = query.get_time_series_data(days)
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid query_type. Supported types: by_ticket_id, by_priority, by_state, by_source, summary, time_series'
                })
            }
        
        return {
            'statusCode': 200 if result.get('success', True) else 400,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


