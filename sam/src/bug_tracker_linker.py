import os
import boto3
import json
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'BugTracker')
table = dynamodb.Table(table_name)


class BugTrackerLinker:
    def __init__(self):
        self.table = table
    
    def get_bug_details(self, ticket_id):
        """Get all records for a specific ticket ID"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :ticket_id',
                ExpressionAttributeValues={
                    ':ticket_id': ticket_id
                }
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error getting bug details: {str(e)}")
            return []
    
    def link_bugs(self, old_ticket_id, new_ticket_id):
        """
        Link bugs by updating the PK (ticketId).
        This implements the "one-time migration item" from the update strategy.
        """
        try:
            # Get all records for the old ticket ID
            old_records = self.get_bug_details(old_ticket_id)
            
            if not old_records:
                logger.warning(f"No records found for ticket ID: {old_ticket_id}")
                return {
                    'success': False,
                    'message': f'No records found for ticket ID: {old_ticket_id}',
                    'linked_count': 0
                }
            
            logger.info(f"Linking {len(old_records)} records from {old_ticket_id} to {new_ticket_id}")
            
            linked_count = 0
            # Update each record with the new ticket ID
            for record in old_records:
                try:
                    # Create new item with updated PK
                    new_item = record.copy()
                    new_item['PK'] = new_ticket_id
                    new_item['updatedAt'] = datetime.now().isoformat()
                    
                    # Delete old item and insert new item
                    self.table.delete_item(
                        Key={
                            'PK': old_ticket_id,
                            'SK': record['SK']
                        }
                    )
                    
                    self.table.put_item(Item=new_item)
                    linked_count += 1
                    logger.info(f"Updated: {record['SK']}")
                    
                except Exception as e:
                    logger.error(f"Error updating record {record['SK']}: {str(e)}")
                    continue
            
            logger.info(f"Successfully linked {linked_count} records to {new_ticket_id}")
            return {
                'success': True,
                'message': f'Successfully linked {linked_count} records to {new_ticket_id}',
                'linked_count': linked_count,
                'old_ticket_id': old_ticket_id,
                'new_ticket_id': new_ticket_id
            }
            
        except Exception as e:
            logger.error(f"Error linking bugs: {str(e)}")
            return {
                'success': False,
                'message': f'Error linking bugs: {str(e)}',
                'linked_count': 0
            }
    
    def create_synthetic_ticket(self, slack_msg_id, zendesk_ticket_id):
        """
        Create a synthetic ticket ID when PM links a real Zendesk ticket.
        This implements the fallback strategy from the images.
        """
        synthetic_id = f"SL-{slack_msg_id}"
        return self.link_bugs(synthetic_id, zendesk_ticket_id)
    
    def show_bug_summary(self, ticket_id):
        """Show a summary of all records for a ticket ID"""
        records = self.get_bug_details(ticket_id)
        
        if not records:
            return {
                'success': False,
                'message': f'No records found for ticket ID: {ticket_id}',
                'records': []
            }
        
        summary = {
            'ticket_id': ticket_id,
            'total_records': len(records),
            'records': []
        }
        
        for record in records:
            source = record.get('sourceSystem', 'unknown')
            sk = record.get('SK', '')
            
            record_summary = {
                'source_system': source,
                'sort_key': sk,
                'created_at': record.get('createdAt', 'unknown')
            }
            
            if source == 'slack':
                record_summary['content'] = record.get('text', 'No text')[:100] + "..."
            elif source == 'zendesk':
                record_summary['content'] = record.get('subject', 'No subject')[:100] + "..."
                record_summary['status'] = record.get('status', 'unknown')
            elif source == 'shortcut':
                record_summary['content'] = record.get('name', 'No name')[:100] + "..."
                record_summary['state'] = record.get('state', 'unknown')
            
            summary['records'].append(record_summary)
        
        return {
            'success': True,
            'summary': summary
        }
    
    def list_unlinked_slack_bugs(self):
        """List Slack bugs that don't have Zendesk tickets linked"""
        try:
            response = self.table.query(
                IndexName='source-index',
                KeyConditionExpression='sourceSystem = :source_system',
                FilterExpression='begins_with(PK, :sl_prefix)',
                ExpressionAttributeValues={
                    ':source_system': 'slack',
                    ':sl_prefix': 'SL-'
                }
            )
            
            unlinked_bugs = response.get('Items', [])
            
            if not unlinked_bugs:
                return {
                    'success': True,
                    'message': 'All Slack bugs are linked to Zendesk tickets',
                    'unlinked_count': 0,
                    'unlinked_bugs': []
                }
            
            bug_list = []
            for bug in unlinked_bugs:
                ticket_id = bug.get('PK', 'unknown')
                text = bug.get('text', 'No text')[:200] + "..."
                created = bug.get('createdAt', 'unknown')
                
                bug_list.append({
                    'ticket_id': ticket_id,
                    'text': text,
                    'created_at': created
                })
            
            return {
                'success': True,
                'message': f'Found {len(unlinked_bugs)} unlinked Slack bugs',
                'unlinked_count': len(unlinked_bugs),
                'unlinked_bugs': bug_list
            }
            
        except Exception as e:
            logger.error(f"Error listing unlinked Slack bugs: {str(e)}")
            return {
                'success': False,
                'message': f'Error listing unlinked Slack bugs: {str(e)}',
                'unlinked_count': 0,
                'unlinked_bugs': []
            }


def lambda_handler(event, context):
    """
    Lambda handler for BugTracker linking operations
    """
    try:
        # Parse the request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        action = body.get('action', '')
        linker = BugTrackerLinker()
        
        if action == 'link_bugs':
            old_ticket_id = body.get('old_ticket_id')
            new_ticket_id = body.get('new_ticket_id')
            
            if not old_ticket_id or not new_ticket_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameters: old_ticket_id and new_ticket_id'
                    })
                }
            
            result = linker.link_bugs(old_ticket_id, new_ticket_id)
            
        elif action == 'create_synthetic_link':
            slack_msg_id = body.get('slack_msg_id')
            zendesk_ticket_id = body.get('zendesk_ticket_id')
            
            if not slack_msg_id or not zendesk_ticket_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameters: slack_msg_id and zendesk_ticket_id'
                    })
                }
            
            if not zendesk_ticket_id.startswith('ZD-'):
                zendesk_ticket_id = f"ZD-{zendesk_ticket_id}"
            
            result = linker.create_synthetic_ticket(slack_msg_id, zendesk_ticket_id)
            
        elif action == 'show_bug_summary':
            ticket_id = body.get('ticket_id')
            
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: ticket_id'
                    })
                }
            
            result = linker.show_bug_summary(ticket_id)
            
        elif action == 'list_unlinked_slack_bugs':
            result = linker.list_unlinked_slack_bugs()
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid action. Supported actions: link_bugs, create_synthetic_link, show_bug_summary, list_unlinked_slack_bugs'
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


