import os
import boto3
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'BugTracker')
table = dynamodb.Table(table_name)

# Shortcut translation mappings - Real names from Shortcut API
SHORTCUT_USER_MAPPING = {
    "624b2310-61a8-4023-b0b8-57a0ecbe2656": "Ryan Foley",
    "6356c7de-9fc9-4b06-aadf-1b2857238974": "Jorge Pasco", 
    "6728fdb5-7a98-4700-abec-6f8259aa4464": "Matheus Lopes",
    "66424177-3c6b-4160-b1c2-3c8799fe5df9": "Chris Wang",
    "66424177-d9af-43c0-9f9c-21eb4b0d5587": "Francisco Pantoja",
    "6668c6f1-f038-4d71-b053-e6ef337bcde6": "Javier Delgado",
    "67c5f99f-bd86-4589-8957-808426bcbfaa": "Sierra Millard",
    "5f20af12-be80-4d17-955a-27ae02a5d823": "Rum Sheikhani",
    "5f178286-65b0-4adb-9d3d-b453a383c450": "Caitlin Lee",
    "617c3d57-d301-4c63-be27-06159d6c3905": "Erica Ellingson"
}

SHORTCUT_STATUS_MAPPING = {
    "500000027": "Ready for Dev",
    "500000043": "In Progress", 
    "500000385": "Code Review",
    "500003719": "Ready for QA",
    "500009065": "Blocked",
    "500000028": "Released",
    "500000380": "To Do",
    "500008605": "Ready for Release",
    "500000042": "Ready for Tech Design Review",
    "500000063": "1st Refinement",
    "500012485": "Backlog Refinement",
    "500012489": "3rd Refinement"
}


def translate_shortcut_item(item):
    """Translate Shortcut IDs to readable names for a single item"""
    if item.get('sourceSystem') == 'shortcut':
        # Translate assignee ID to name
        if item.get('assignee') and item['assignee'] in SHORTCUT_USER_MAPPING:
            item['assignee'] = SHORTCUT_USER_MAPPING[item['assignee']]
        elif item.get('assignee') and item['assignee'] != 'Unassigned':
            item['assignee'] = item['assignee'][:8]  # Show partial ID if not mapped
            
        # Translate status ID to name (extract ID from "Unknown (ID)" format)
        if item.get('status') and item['status'].startswith('Unknown (') and item['status'].endswith(')'):
            status_id = item['status'][9:-1]  # Extract ID from "Unknown (500000027)"
            if status_id in SHORTCUT_STATUS_MAPPING:
                item['status'] = SHORTCUT_STATUS_MAPPING[status_id]
                
        # Also fix the state field if it has the same format
        if item.get('state') and '_(' in item['state']:
            state_parts = item['state'].split('_(')
            if len(state_parts) == 2 and state_parts[1].endswith(')'):
                status_id = state_parts[1][:-1]
                if status_id in SHORTCUT_STATUS_MAPPING:
                    # Map to normalized states
                    status_name = SHORTCUT_STATUS_MAPPING[status_id]
                    if status_name in ['Done', 'Complete']:
                        item['state'] = 'closed'
                    elif status_name in ['Ready for Dev', 'To Do', 'Backlog']:
                        item['state'] = 'open'
                    elif status_name in ['In Progress', 'Code Review', 'Ready for QA', 'QA Testing', 'Design Review']:
                        item['state'] = 'in_progress'
                    elif status_name in ['Blocked']:
                        item['state'] = 'blocked'
                    elif status_name in ['Needs Review', 'Under Review']:
                        item['state'] = 'pending'
    return item

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
            
            items = response.get('Items', [])
            # Translate Shortcut items
            items = [translate_shortcut_item(item) for item in items]
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': items
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
            
            items = response.get('Items', [])
            
            # Translate Shortcut items
            items = [translate_shortcut_item(item) for item in items]
            
            # Sort by creation date (newest first)
            items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': items,
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
            key_condition = '#st = :state'
            expression_values = {':state': state}
            expression_names = {'#st': 'state'}
            
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
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            
            items = response.get('Items', [])
            
            # Translate Shortcut items
            items = [translate_shortcut_item(item) for item in items]
            
            # Sort by creation date (newest first)
            items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': items,
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
            
            items = response.get('Items', [])
            
            # Translate Shortcut items
            items = [translate_shortcut_item(item) for item in items]
            
            # Sort by creation date (newest first)
            items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            
            return {
                'success': True,
                'count': response.get('Count', 0),
                'items': items,
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

    def get_all_bugs(self, limit=None, order_by='newest'):
        """Get all bugs with optional limit and ordering"""
        try:
            # Set a reasonable default limit to improve performance
            if limit is None:
                limit = 1000  # Default limit for better performance
            
            scan_kwargs = {
                'Limit': int(limit)
            }
            
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # Translate Shortcut items
            items = [translate_shortcut_item(item) for item in items]
            
            # Sort by creation date (newest first by default)
            if order_by == 'newest':
                items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            elif order_by == 'oldest':
                items.sort(key=lambda x: x.get('createdAt', ''), reverse=False)
            
            return {
                'success': True,
                'items': items,
                'count': len(items),
                'total_scanned': response.get('ScannedCount', 0),
                'has_more': 'LastEvaluatedKey' in response
            }
        except Exception as e:
            logger.error(f"Error getting all bugs: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_bugs_summary(self, time_range=None, source_system=None):
        """Get summary statistics for all bugs, optionally filtered by source system"""
        try:
            if source_system:
                # Get bugs from specific source and count by priority/state
                source_result = self.get_bugs_by_source(source_system, time_range)
                if not source_result['success']:
                    return source_result
                
                bugs = source_result['items']
                
                # Count by priority
                priorities = ['High', 'Medium', 'Low', 'Critical', 'Unknown']
                priority_counts = {priority: 0 for priority in priorities}
                
                # Count by state
                states = ['open', 'closed', 'pending', 'Ready for Dev', 'In Progress', 'Ready for QA', 'Blocked']
                state_counts = {state: 0 for state in states}
                
                # Count by source (will be only one source)
                sources = ['slack', 'zendesk', 'shortcut']
                source_counts = {source: 0 for source in sources}
                source_counts[source_system] = len(bugs)
                
                # Count bugs by priority and state
                for bug in bugs:
                    priority = bug.get('priority', 'Unknown')
                    if priority in priority_counts:
                        priority_counts[priority] += 1
                    else:
                        priority_counts['Unknown'] += 1
                    
                    state = bug.get('state', 'open')
                    if state in state_counts:
                        state_counts[state] += 1
                    else:
                        state_counts['open'] += 1
                
                total_bugs = len(bugs)
            else:
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
                    'total': total_bugs,
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
    
    def get_time_series_data(self, days=7, source_system=None):
        """Get time series data of new bugs over time, optionally filtered by source system"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for DynamoDB query
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            # Query bugs in the time range, optionally filtered by source
            if source_system:
                response = self.table.scan(
                    FilterExpression='createdAt BETWEEN :start_date AND :end_date AND sourceSystem = :source_system',
                    ExpressionAttributeValues={
                        ':start_date': start_date_str,
                        ':end_date': end_date_str,
                        ':source_system': source_system
                    }
                )
            else:
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


def get_cors_headers():
    """Returns CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Content-Type': 'application/json'
    }


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise to float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """
    Lambda handler for BugTracker query operations
    """
    try:
        # Parse the request - handle both API Gateway and direct invocation
        if 'queryStringParameters' in event and event['queryStringParameters']:
            # API Gateway GET request with query parameters
            query_params = event['queryStringParameters']
            query_type = query_params.get('query_type', '')
            time_range = query_params.get('time_range')
        elif 'body' in event and event['body']:
            # API Gateway POST request or direct invocation with body
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            query_type = body.get('query_type', '')
            query_params = body.get('params', {})
            time_range = body.get('time_range')
        else:
            # Direct invocation or empty request
            body = event if event else {}
            query_type = body.get('query_type', '')
            query_params = body.get('params', {})
            time_range = body.get('time_range')
        
        query = BugTrackerQuery()
        
        if query_type == 'by_ticket_id':
            ticket_id = query_params.get('ticket_id')
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
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
                    'headers': get_cors_headers(),
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
                    'headers': get_cors_headers(),
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
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'error': 'Missing required parameter: source_system'
                    })
                }
            result = query.get_bugs_by_source(source_system, time_range)
            
        elif query_type == 'summary':
            source_system = query_params.get('source_system')
            result = query.get_bugs_summary(time_range, source_system)
            
        elif query_type == 'time_series':
            days = int(query_params.get('days', 7))
            source_system = query_params.get('source_system')
            result = query.get_time_series_data(days, source_system)
            
        elif query_type == 'list':
            limit = query_params.get('limit')
            order_by = query_params.get('order_by', 'newest')
            result = query.get_all_bugs(limit, order_by)
            
        else:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid query_type. Supported types: by_ticket_id, by_priority, by_state, by_source, summary, time_series, list'
                })
            }
        
        return {
            'statusCode': 200 if result.get('success', True) else 400,
            'headers': get_cors_headers(),
            'body': json.dumps(result, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


