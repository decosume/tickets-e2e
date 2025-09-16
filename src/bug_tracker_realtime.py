#!/usr/bin/env python3
"""
Real-time WebSocket handler for bug tracker updates.
Manages WebSocket connections and broadcasts events to connected clients.
"""

import json
import boto3
import os
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
apigateway = boto3.client('apigatewaymanagementapi')

# Tables
connections_table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE', 'BugTrackerConnections'))
bugs_table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'BugTracker-evt-bugtracker'))

def lambda_handler(event, context):
    """Handle WebSocket events."""
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    if route_key == '$connect':
        return handle_connect(connection_id, event)
    elif route_key == '$disconnect':
        return handle_disconnect(connection_id)
    elif route_key == 'subscribe':
        return handle_subscribe(connection_id, event)
    else:
        return {'statusCode': 400, 'body': 'Unknown route'}

def handle_connect(connection_id, event):
    """Handle new WebSocket connection."""
    try:
        # Store connection info
        connections_table.put_item(
            Item={
                'connectionId': connection_id,
                'connectedAt': datetime.utcnow().isoformat(),
                'subscriptions': [],  # Will be populated by subscribe events
                'userAgent': event.get('headers', {}).get('User-Agent', ''),
                'sourceIp': event.get('requestContext', {}).get('identity', {}).get('sourceIp', '')
            }
        )
        
        logger.info(f"New WebSocket connection: {connection_id}")
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error handling connect: {str(e)}")
        return {'statusCode': 500}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnection."""
    try:
        connections_table.delete_item(Key={'connectionId': connection_id})
        logger.info(f"WebSocket disconnected: {connection_id}")
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error handling disconnect: {str(e)}")
        return {'statusCode': 500}

def handle_subscribe(connection_id, event):
    """Handle subscription to specific bug updates."""
    try:
        body = json.loads(event.get('body', '{}'))
        subscription_type = body.get('type', 'all')  # 'all', 'priority', 'assignee', etc.
        filters = body.get('filters', {})
        
        # Update connection with subscription info
        connections_table.update_item(
            Key={'connectionId': connection_id},
            UpdateExpression='SET subscriptions = :subs',
            ExpressionAttributeValues={
                ':subs': {
                    'type': subscription_type,
                    'filters': filters,
                    'subscribedAt': datetime.utcnow().isoformat()
                }
            }
        )
        
        # Send confirmation
        send_to_connection(connection_id, {
            'type': 'subscription_confirmed',
            'subscription': {'type': subscription_type, 'filters': filters}
        })
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error handling subscribe: {str(e)}")
        return {'statusCode': 500}

def send_to_connection(connection_id, message):
    """Send message to specific WebSocket connection."""
    try:
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except apigateway.exceptions.GoneException:
        # Connection is stale, remove it
        connections_table.delete_item(Key={'connectionId': connection_id})
        logger.info(f"Removed stale connection: {connection_id}")
    except Exception as e:
        logger.error(f"Error sending to connection {connection_id}: {str(e)}")

def broadcast_bug_update(bug_data, event_type):
    """Broadcast bug update to all relevant subscribers."""
    try:
        # Get all active connections
        response = connections_table.scan()
        connections = response.get('Items', [])
        
        # Prepare the message
        message = {
            'type': event_type,  # 'bug_created', 'bug_updated', 'bug_resolved'
            'timestamp': datetime.utcnow().isoformat(),
            'bug': bug_data
        }
        
        # Send to relevant subscribers
        for connection in connections:
            connection_id = connection['connectionId']
            subscriptions = connection.get('subscriptions', {})
            
            if should_send_to_subscriber(bug_data, subscriptions):
                send_to_connection(connection_id, message)
        
        logger.info(f"Broadcasted {event_type} to {len(connections)} connections")
        
    except Exception as e:
        logger.error(f"Error broadcasting update: {str(e)}")

def should_send_to_subscriber(bug_data, subscriptions):
    """Determine if bug update should be sent to subscriber based on their filters."""
    if not subscriptions:
        return True  # Send to all if no specific subscriptions
    
    sub_type = subscriptions.get('type', 'all')
    filters = subscriptions.get('filters', {})
    
    if sub_type == 'all':
        return True
    elif sub_type == 'priority':
        return bug_data.get('priority') in filters.get('priorities', [])
    elif sub_type == 'source':
        return bug_data.get('source_system') in filters.get('sources', [])
    elif sub_type == 'assignee':
        return bug_data.get('assignee') in filters.get('assignees', [])
    
    return False

# Event handler for DynamoDB Streams
def handle_dynamodb_stream(event, context):
    """Handle DynamoDB stream events for real-time updates."""
    try:
        for record in event.get('Records', []):
            event_name = record.get('eventName')  # INSERT, MODIFY, REMOVE
            
            if event_name in ['INSERT', 'MODIFY']:
                # Get the bug data
                if event_name == 'INSERT':
                    bug_data = record['dynamodb']['NewImage']
                    event_type = 'bug_created'
                else:
                    bug_data = record['dynamodb']['NewImage']
                    event_type = 'bug_updated'
                
                # Convert DynamoDB format to regular format
                bug_data = convert_dynamodb_to_json(bug_data)
                
                # Only process bug records (not connections)
                if bug_data.get('PK', '').startswith(('SL-', 'ZD-', 'SC-')):
                    broadcast_bug_update(bug_data, event_type)
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error handling DynamoDB stream: {str(e)}")
        return {'statusCode': 500}

def convert_dynamodb_to_json(dynamodb_item):
    """Convert DynamoDB item format to regular JSON."""
    def convert_value(value):
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            return float(value['N'])
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'L' in value:
            return [convert_value(item) for item in value['L']]
        elif 'M' in value:
            return {k: convert_value(v) for k, v in value['M'].items()}
        return value
    
    return {key: convert_value(value) for key, value in dynamodb_item.items()}
