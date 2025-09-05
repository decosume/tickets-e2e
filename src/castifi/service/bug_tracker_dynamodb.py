import os
import re
import boto3
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "BugTracker")

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


class BugTrackerDynamoDB:
    def __init__(self):
        self.table_name = DYNAMODB_TABLE
        self.table = None
        
    def create_table(self):
        """Create BugTracker DynamoDB table with the unified schema"""
        try:
            # Check if table exists
            try:
                self.table = dynamodb.Table(self.table_name)
                self.table.load()
                print(f"ℹ️  Table '{self.table_name}' already exists")
                return self.table
            except dynamodb_client.exceptions.ResourceNotFoundException:
                pass
            
            # Create table with unified schema
            self.table = dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'PK',  # ticketId
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'SK',  # sourceSystem#recordId
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'priority',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'state',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'sourceSystem',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'createdAt',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'priority-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'priority',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'createdAt',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    },
                    {
                        'IndexName': 'state-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'state',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'createdAt',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    },
                    {
                        'IndexName': 'source-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'sourceSystem',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'createdAt',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            self.table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            print(f"✅ Table '{self.table_name}' created successfully with unified schema")
            return self.table
            
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            raise
    
    def upsert_bug_item(self, ticket_id, source_system, record_id, attributes):
        """
        Upsert a bug item following the unified schema.
        
        Args:
            ticket_id: The unified ticket ID (e.g., ZD-12345, SC-56789, SL-9876543210.12345)
            source_system: The source system (slack, zendesk, shortcut)
            record_id: The record ID from the source system
            attributes: Dictionary of attributes to store
        """
        try:
            # Create the sort key
            sk = f"{source_system}#{record_id}"
            
            # Prepare the item
            item = {
                'PK': ticket_id,
                'SK': sk,
                'sourceSystem': source_system,
                'createdAt': attributes.get('createdAt', datetime.now().isoformat()),
                'updatedAt': datetime.now().isoformat()
            }
            
            # Add all other attributes
            for key, value in attributes.items():
                if key not in ['PK', 'SK', 'sourceSystem', 'createdAt', 'updatedAt']:
                    if isinstance(value, (dict, list)):
                        item[key] = json.dumps(value)
                    else:
                        item[key] = value
            
            # Upsert the item
            self.table.put_item(Item=item)
            print(f"📝 Upserted [{ticket_id}] from [{source_system}] → {attributes.get('subject', attributes.get('text', attributes.get('name', 'No title')))}")
            
        except Exception as e:
            print(f"❌ Error upserting item: {str(e)}")
            raise
    
    def get_bug_by_ticket_id(self, ticket_id):
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
            print(f"❌ Error querying by ticket ID: {str(e)}")
            return []
    
    def get_bugs_by_priority(self, priority):
        """Get all bugs by priority using GSI"""
        try:
            response = self.table.query(
                IndexName='priority-index',
                KeyConditionExpression='priority = :priority',
                ExpressionAttributeValues={
                    ':priority': priority
                }
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"❌ Error querying by priority: {str(e)}")
            return []
    
    def get_bugs_by_state(self, state):
        """Get all bugs by state using GSI"""
        try:
            response = self.table.query(
                IndexName='state-index',
                KeyConditionExpression='state = :state',
                ExpressionAttributeValues={
                    ':state': state
                }
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"❌ Error querying by state: {str(e)}")
            return []
    
    def get_bugs_by_source(self, source_system):
        """Get all bugs by source system using GSI"""
        try:
            response = self.table.query(
                IndexName='source-index',
                KeyConditionExpression='sourceSystem = :source_system',
                ExpressionAttributeValues={
                    ':source_system': source_system
                }
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"❌ Error querying by source: {str(e)}")
            return []


class BugDataIngestion:
    def __init__(self):
        self.dynamodb = BugTrackerDynamoDB()
    
    def extract_ticket_info_from_slack(self, text):
        """Extract ticketId and priority if available, fallback if not."""
        ticket_pattern = re.search(r"ticketId[:=]\s*(\S+)", text, re.IGNORECASE)
        priority_pattern = re.search(r"priority[:=]\s*(\S+)", text, re.IGNORECASE)

        ticket_id = ticket_pattern.group(1) if ticket_pattern else f"SL-{hash(text)}"
        priority = priority_pattern.group(1).capitalize() if priority_pattern else "Unknown"

        return ticket_id, priority
    
    def fetch_slack_messages(self):
        """Fetch Slack messages and normalize into bug records."""
        print("📨 Fetching Slack messages...")
        
        try:
            url = "https://slack.com/api/conversations.history"
            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
            params = {"channel": SLACK_CHANNEL_ID, "limit": 50}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            messages = data.get("messages", []) if data.get("ok") else []
            results = []

            for msg in messages:
                text = msg.get("text", "")
                ticket_id, priority = self.extract_ticket_info_from_slack(text)
                msg_id = msg.get("ts", str(time.time()))

                bug_data = {
                    "author": msg.get("user", "unknown"),
                    "text": text,
                    "priority": priority,
                    "createdAt": datetime.fromtimestamp(float(msg["ts"])).isoformat()
                }
                
                self.dynamodb.upsert_bug_item(ticket_id, "slack", msg_id, bug_data)
                results.append((ticket_id, bug_data))

            print(f"✅ {len(results)} Slack records processed")
            return results

        except Exception as e:
            print(f"❌ Error fetching Slack messages: {str(e)}")
            return []
    
    def fetch_zendesk_tickets(self):
        """Fetch Zendesk tickets and normalize into bug records."""
        print("🎫 Fetching Zendesk tickets...")
        
        try:
            url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
            auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
            response = requests.get(url, auth=auth, timeout=10)
            response.raise_for_status()

            data = response.json()
            tickets = data.get("tickets", [])
            results = []

            for t in tickets:
                if "bug" not in (t.get("tags") or []):  # filter only bug tickets
                    continue

                ticket_id = f"ZD-{t['id']}"
                bug_data = {
                    "requester": t.get("requester_id"),
                    "assignee": t.get("assignee_id"),
                    "priority": t.get("priority", "Unknown"),
                    "status": t.get("status", "open"),
                    "subject": t.get("subject", ""),
                    "createdAt": t.get("created_at"),
                    "updatedAt": t.get("updated_at")
                }
                
                self.dynamodb.upsert_bug_item(ticket_id, "zendesk", str(t['id']), bug_data)
                results.append((ticket_id, bug_data))

            print(f"✅ {len(results)} Zendesk records processed")
            return results

        except Exception as e:
            print(f"❌ Error fetching Zendesk tickets: {str(e)}")
            return []
    
    def fetch_shortcut_bugs(self):
        """Fetch Shortcut bugs and normalize into bug records."""
        print("📋 Fetching Shortcut bugs...")
        
        try:
            query = (
                "type:bug "
                "(workflow_state_id:500000027 OR workflow_state_id:500000043 "
                "OR workflow_state_id:500000385 OR workflow_state_id:500003719 OR workflow_state_id:500009065) "
                "-state:Complete"
            )

            url = "https://api.app.shortcut.com/api/v3/search/stories"
            headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
            params = {"query": query, "page_size": 25}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            bugs = data.get("data", [])
            results = []

            for bug in bugs:
                ticket_id = None
                if bug.get("name") and "ZD-" in bug["name"]:  # try to extract Zendesk ID
                    match = re.search(r"(ZD-\d+)", bug["name"])
                    if match:
                        ticket_id = match.group(1)

                if not ticket_id:
                    ticket_id = f"SC-{bug['id']}"

                # Map workflow state ID to readable name
                workflow_state_id = bug.get('workflow_state_id')
                status_name = {
                    "500000027": "Ready for Dev",
                    "500000043": "In Progress", 
                    "500000385": "Code Review",
                    "500003719": "Ready for QA",
                    "500009065": "Blocked"
                }.get(workflow_state_id, f"Unknown ({workflow_state_id})")

                bug_data = {
                    "shortcut_story_id": bug["id"],
                    "name": bug.get("name", ""),
                    "state": status_name,
                    "createdAt": bug.get("created_at"),
                    "updatedAt": bug.get("updated_at"),
                    "completed": bug.get("completed", False),
                    "archived": bug.get("archived", False)
                }
                
                self.dynamodb.upsert_bug_item(ticket_id, "shortcut", str(bug['id']), bug_data)
                results.append((ticket_id, bug_data))

            print(f"✅ {len(results)} Shortcut records processed")
            return results

        except Exception as e:
            print(f"❌ Error fetching Shortcut bugs: {str(e)}")
            return []
    
    def ingest_all_data(self):
        """Ingest data from all sources using the unified schema"""
        print("🚀 Starting BugTracker data ingestion...")
        print()
        
        # Create table with unified schema
        self.dynamodb.create_table()
        print()
        
        # Fetch data from all sources
        slack_records = self.fetch_slack_messages()
        zendesk_records = self.fetch_zendesk_tickets()
        shortcut_records = self.fetch_shortcut_bugs()
        
        total_records = len(slack_records) + len(zendesk_records) + len(shortcut_records)
        print(f"\n🎯 Ingestion complete. Total records processed: {total_records}")
        
        return total_records


def main():
    """Main function to run unified bug tracking ingestion"""
    print("=" * 60)
    print("🐛 UNIFIED BUG TRACKER DYNAMODB INGESTION")
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
    ingestion = BugDataIngestion()
    total_records = ingestion.ingest_all_data()
    
    print()
    print("=" * 60)
    print(f"📊 INGESTION SUMMARY: {total_records} records processed")
    print("=" * 60)
    print()
    print("🎯 Next steps:")
    print("1. Configure Grafana to connect to DynamoDB")
    print("2. Create dashboard queries using the GSIs:")
    print("   - priority-index: Count bugs by priority")
    print("   - state-index: Count bugs by state/status")
    print("   - source-index: Count bugs by source system")
    print("3. Set up automated ingestion scheduling")
    print("4. Implement manual linking for cross-system bugs")


if __name__ == "__main__":
    main()


