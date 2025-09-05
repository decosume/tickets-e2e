import os
import boto3
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "support_data_ingestion")

# API Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
SHORTCUT_API_TOKEN = os.getenv("SHORTCUT_API_TOKEN")

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)


class DynamoDBDataStorage:
    def __init__(self):
        self.table_name = DYNAMODB_TABLE
        
    def create_table(self):
        """Create DynamoDB table if it doesn't exist"""
        try:
            # Check if table exists
            try:
                table = dynamodb.Table(self.table_name)
                table.load()
                print(f"ℹ️  Table '{self.table_name}' already exists")
                return table
            except dynamodb_client.exceptions.ResourceNotFoundException:
                pass
            
            # Create table
            table = dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'data_type',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'unique_id',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'data_type',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'unique_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            print(f"✅ Table '{self.table_name}' created successfully")
            return table
            
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            raise
    
    def write_records(self, records):
        """Write records to DynamoDB"""
        if not records:
            return
        
        try:
            # Remove duplicates based on unique_id
            seen_ids = set()
            unique_records = []
            for record in records:
                unique_id = record.get('unique_id')
                if unique_id not in seen_ids:
                    seen_ids.add(unique_id)
                    unique_records.append(record)
            
            print(f"📝 Deduplicated {len(records)} records to {len(unique_records)} unique records")
            
            table = dynamodb.Table(self.table_name)
            
            # Write records in batches
            with table.batch_writer() as batch:
                for record in unique_records:
                    batch.put_item(Item=record)
            
            print(f"✅ Wrote {len(unique_records)} records to DynamoDB")
        except Exception as e:
            print(f"❌ Error writing records: {str(e)}")
            raise
    
    def create_dynamodb_record(self, data_type, source, data, timestamp=None):
        """Create a DynamoDB record"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
        
        # Create unique identifier using more specific data
        if data_type == 'slack_message':
            unique_id = f"{data_type}_{data.get('message_id', '')}_{timestamp}"
        elif data_type == 'zendesk_ticket':
            unique_id = f"{data_type}_{data.get('ticket_id', '')}_{timestamp}"
        elif data_type == 'shortcut_epic':
            unique_id = f"{data_type}_{data.get('epic_id', '')}_{timestamp}"
        elif data_type == 'shortcut_iteration':
            unique_id = f"{data_type}_{data.get('iteration_id', '')}_{timestamp}"
        else:
            unique_id = f"{data_type}_{timestamp}_{hash(str(data))}"
        
        record = {
            'data_type': data_type,
            'timestamp': timestamp,
            'unique_id': unique_id,  # Add unique identifier
            'source': source,
            'created_at': datetime.now().isoformat()
        }
        
        # Add data fields
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                record[key] = value
            elif isinstance(value, dict):
                record[key] = json.dumps(value)
            elif isinstance(value, list):
                record[key] = json.dumps(value)
        
        return record


class DataIngestion:
    def __init__(self):
        self.dynamodb = DynamoDBDataStorage()
    
    def fetch_slack_data(self):
        """Fetch and process Slack data"""
        print("📨 Fetching Slack data...")
        
        try:
            # Fetch channel messages
            url = "https://slack.com/api/conversations.history"
            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
            params = {"channel": SLACK_CHANNEL_ID, "limit": 100}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("ok"):
                print(f"❌ Slack API error: {data.get('error')}")
                return []
            
            messages = data.get("messages", [])
            records = []
            
            for msg in messages:
                # Convert timestamp to milliseconds
                ts = int(float(msg.get('ts', 0)) * 1000)
                
                record_data = {
                    'message_id': msg.get('client_msg_id', ''),
                    'user_id': msg.get('user', ''),
                    'text': msg.get('text', '')[:500],  # Truncate long messages
                    'type': msg.get('type', ''),
                    'subtype': msg.get('subtype', ''),
                    'has_attachments': bool(msg.get('attachments')),
                    'has_reactions': bool(msg.get('reactions')),
                    'thread_ts': msg.get('thread_ts', ''),
                    'reply_count': msg.get('reply_count', 0),
                    'reply_users_count': msg.get('reply_users_count', 0)
                }
                
                record = self.dynamodb.create_dynamodb_record(
                    'slack_message',
                    'urgent-vouchers',
                    record_data,
                    ts
                )
                records.append(record)
            
            print(f"📊 Processed {len(records)} Slack messages")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching Slack data: {str(e)}")
            return []
    
    def fetch_zendesk_data(self):
        """Fetch and process Zendesk data"""
        print("🎫 Fetching Zendesk data...")
        
        try:
            url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
            auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
            response = requests.get(url, auth=auth, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tickets = data.get("tickets", [])
            records = []
            
            for ticket in tickets:
                # Convert created_at to timestamp
                created_at = datetime.fromisoformat(ticket.get('created_at', '').replace('Z', '+00:00'))
                ts = int(created_at.timestamp() * 1000)
                
                record_data = {
                    'ticket_id': str(ticket.get('id', '')),
                    'subject': ticket.get('subject', '')[:200],
                    'status': ticket.get('status', ''),
                    'priority': ticket.get('priority', ''),
                    'type': ticket.get('type', ''),
                    'assignee_id': str(ticket.get('assignee_id', '')),
                    'requester_id': str(ticket.get('requester_id', '')),
                    'organization_id': str(ticket.get('organization_id', '')),
                    'tags': ticket.get('tags', []),
                    'has_attachments': ticket.get('has_incidents', False),
                    'satisfaction_rating': ticket.get('satisfaction_rating', {}).get('score', ''),
                    'due_at': ticket.get('due_at', ''),
                    'updated_at': ticket.get('updated_at', '')
                }
                
                record = self.dynamodb.create_dynamodb_record(
                    'zendesk_ticket',
                    'everyset_support',
                    record_data,
                    ts
                )
                records.append(record)
            
            print(f"📊 Processed {len(records)} Zendesk tickets")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching Zendesk data: {str(e)}")
            return []
    
    def fetch_shortcut_data(self):
        """Fetch and process Shortcut data"""
        print("📋 Fetching Shortcut data...")
        
        try:
            records = []
            
            # Fetch bugs using the same query from support-data-ingestion.py
            query = "type:bug (workflow_state_id:500000027 OR workflow_state_id:500000043 OR workflow_state_id:500000385 OR workflow_state_id:500003719 OR workflow_state_id:500009065 OR workflow_state_id:500000026 OR workflow_state_id:500008605 OR workflow_state_id:500000028 OR workflow_state_id:500000042 OR workflow_state_id:500012452 OR workflow_state_id:500000611 OR workflow_state_id:500009066 OR workflow_state_id:500002973 OR workflow_state_id:500006943)"
            
            url = "https://api.app.shortcut.com/api/v3/search/stories"
            headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
            params = {
                "query": query,
                "page_size": 25
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            bugs = data.get('data', [])
            
            for bug in bugs:
                created_at = datetime.fromisoformat(bug.get('created_at', '').replace('Z', '+00:00'))
                ts = int(created_at.timestamp() * 1000)
                
                # Map workflow state ID to readable name
                workflow_state_id = bug.get('workflow_state_id')
                status_name = {
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
                }.get(workflow_state_id, f"Unknown ({workflow_state_id})")
                
                record_data = {
                    'bug_id': str(bug.get('id', '')),
                    'name': bug.get('name', '')[:200],
                    'description': bug.get('description', '')[:500],
                    'story_type': bug.get('story_type', ''),
                    'workflow_state_id': workflow_state_id,
                    'status_name': status_name,
                    'owner_ids': bug.get('owner_ids', []),
                    'labels': bug.get('labels', []),
                    'archived': bug.get('archived', False),
                    'completed': bug.get('completed', False),
                    'updated_at': bug.get('updated_at', ''),
                    'completed_at': bug.get('completed_at', '')
                }
                
                record = self.dynamodb.create_dynamodb_record(
                    'shortcut_bug',
                    'everyset_projects',
                    record_data,
                    ts
                )
                records.append(record)
            
            # Also fetch epics for project overview
            url = "https://api.app.shortcut.com/api/v3/epics"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            epics = response.json()
            for epic in epics:
                created_at = datetime.fromisoformat(epic.get('created_at', '').replace('Z', '+00:00'))
                ts = int(created_at.timestamp() * 1000)
                
                record_data = {
                    'epic_id': str(epic.get('id', '')),
                    'name': epic.get('name', '')[:200],
                    'description': epic.get('description', '')[:500],
                    'state': epic.get('state', ''),
                    'archived': epic.get('archived', False),
                    'started': epic.get('started', False),
                    'completed': epic.get('completed', False),
                    'deadline': epic.get('deadline', ''),
                    'stats': epic.get('stats', {})
                }
                
                record = self.dynamodb.create_dynamodb_record(
                    'shortcut_epic',
                    'everyset_projects',
                    record_data,
                    ts
                )
                records.append(record)
            
            print(f"📊 Processed {len(records)} Shortcut records ({len(bugs)} bugs, {len(epics)} epics)")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching Shortcut data: {str(e)}")
            return []
    
    def ingest_all_data(self):
        """Ingest data from all sources"""
        print("🚀 Starting data ingestion...")
        print()
        
        # Create table
        self.dynamodb.create_table()
        print()
        
        # Fetch data from all sources
        all_records = []
        
        # Slack data
        slack_records = self.fetch_slack_data()
        all_records.extend(slack_records)
        
        # Zendesk data
        zendesk_records = self.fetch_zendesk_data()
        all_records.extend(zendesk_records)
        
        # Shortcut data
        shortcut_records = self.fetch_shortcut_data()
        all_records.extend(shortcut_records)
        
        # Write all records to DynamoDB
        if all_records:
            print(f"📝 Writing {len(all_records)} total records to DynamoDB...")
            self.dynamodb.write_records(all_records)
            print("✅ Data ingestion completed successfully!")
        else:
            print("⚠️  No data to ingest")
        
        return len(all_records)


def main():
    """Main function to run data ingestion"""
    print("=" * 60)
    print("🕒 DYNAMODB DATA INGESTION FOR GRAFANA DASHBOARD")
    print("=" * 60)
    print()
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
        print("✅ AWS credentials verified")
    except Exception as e:
        print(f"❌ AWS credentials error: {str(e)}")
        print("Please configure AWS credentials (aws configure)")
        return
    
    # Initialize and run ingestion
    ingestion = DataIngestion()
    total_records = ingestion.ingest_all_data()
    
    print()
    print("=" * 60)
    print(f"📊 INGESTION SUMMARY: {total_records} records processed")
    print("=" * 60)
    print()
    print("🎯 Next steps:")
    print("1. Configure Grafana to connect to DynamoDB")
    print("2. Create dashboard queries using the data types:")
    print("   - slack_message")
    print("   - zendesk_ticket") 
    print("   - shortcut_bug")
    print("   - shortcut_epic")
    print("3. Set up automated ingestion scheduling")


if __name__ == "__main__":
    main()
