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
TIMESTREAM_DATABASE = os.getenv("TIMESTREAM_DATABASE", "support_data_ingestion")
TIMESTREAM_TABLE = os.getenv("TIMESTREAM_TABLE", "support_metrics")

# API Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
SHORTCUT_API_TOKEN = os.getenv("SHORTCUT_API_TOKEN")

# Initialize AWS Timestream client
timestream_client = boto3.client('timestream-write', region_name=AWS_REGION)
timestream_query_client = boto3.client('timestream-query', region_name=AWS_REGION)


class TimestreamDataStorage:
    def __init__(self):
        self.database_name = TIMESTREAM_DATABASE
        self.table_name = TIMESTREAM_TABLE
        
    def create_database(self):
        """Create Timestream database if it doesn't exist"""
        try:
            timestream_client.create_database(DatabaseName=self.database_name)
            print(f"✅ Database '{self.database_name}' created successfully")
        except timestream_client.exceptions.ConflictException:
            print(f"ℹ️  Database '{self.database_name}' already exists")
        except Exception as e:
            print(f"❌ Error creating database: {str(e)}")
            raise
    
    def create_table(self):
        """Create Timestream table if it doesn't exist"""
        try:
            timestream_client.create_table(
                DatabaseName=self.database_name,
                TableName=self.table_name,
                RetentionProperties={
                    'MemoryStoreRetentionPeriodInHours': 24,
                    'MagneticStoreRetentionPeriodInDays': 365
                }
            )
            print(f"✅ Table '{self.table_name}' created successfully")
        except timestream_client.exceptions.ConflictException:
            print(f"ℹ️  Table '{self.table_name}' already exists")
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            raise
    
    def write_records(self, records):
        """Write records to Timestream"""
        if not records:
            return
        
        try:
            timestream_client.write_records(
                DatabaseName=self.database_name,
                TableName=self.table_name,
                Records=records
            )
            print(f"✅ Wrote {len(records)} records to Timestream")
        except Exception as e:
            print(f"❌ Error writing records: {str(e)}")
            raise
    
    def create_timestream_record(self, data_type, source, data, timestamp=None):
        """Create a Timestream record"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
        
        record = {
            'Dimensions': [
                {'Name': 'data_type', 'Value': data_type},
                {'Name': 'source', 'Value': source}
            ],
            'MeasureName': 'data_point',
            'MeasureValue': '1',
            'MeasureValueType': 'BIGINT',
            'Time': str(timestamp)
        }
        
        # Add data as additional dimensions
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                record['Dimensions'].append({
                    'Name': key,
                    'Value': str(value)
                })
        
        return record


class DataIngestion:
    def __init__(self):
        self.timestream = TimestreamDataStorage()
    
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
                ts = float(msg.get('ts', 0)) * 1000
                
                record_data = {
                    'message_id': msg.get('client_msg_id', ''),
                    'user_id': msg.get('user', ''),
                    'text': msg.get('text', '')[:100],  # Truncate long messages
                    'type': msg.get('type', ''),
                    'subtype': msg.get('subtype', ''),
                    'has_attachments': str(bool(msg.get('attachments'))),
                    'has_reactions': str(bool(msg.get('reactions'))),
                    'thread_ts': msg.get('thread_ts', ''),
                    'reply_count': str(msg.get('reply_count', 0)),
                    'reply_users_count': str(msg.get('reply_users_count', 0))
                }
                
                record = self.timestream.create_timestream_record(
                    'slack_message',
                    'urgent-vouchers',
                    record_data,
                    int(ts)
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
                    'subject': ticket.get('subject', '')[:100],
                    'status': ticket.get('status', ''),
                    'priority': ticket.get('priority', ''),
                    'type': ticket.get('type', ''),
                    'assignee_id': str(ticket.get('assignee_id', '')),
                    'requester_id': str(ticket.get('requester_id', '')),
                    'organization_id': str(ticket.get('organization_id', '')),
                    'tags': ','.join(ticket.get('tags', [])),
                    'has_attachments': str(ticket.get('has_incidents', False)),
                    'satisfaction_rating': str(ticket.get('satisfaction_rating', {}).get('score', '')),
                    'due_at': ticket.get('due_at', ''),
                    'updated_at': ticket.get('updated_at', '')
                }
                
                record = self.timestream.create_timestream_record(
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
            
            # Fetch epics
            url = "https://api.app.shortcut.com/api/v3/epics"
            headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            epics = response.json()
            for epic in epics:
                created_at = datetime.fromisoformat(epic.get('created_at', '').replace('Z', '+00:00'))
                ts = int(created_at.timestamp() * 1000)
                
                record_data = {
                    'epic_id': str(epic.get('id', '')),
                    'name': epic.get('name', '')[:100],
                    'description': epic.get('description', '')[:100],
                    'state': epic.get('state', ''),
                    'archived': str(epic.get('archived', False)),
                    'started': str(epic.get('started', False)),
                    'completed': str(epic.get('completed', False)),
                    'deadline': epic.get('deadline', ''),
                    'stats': json.dumps(epic.get('stats', {}))
                }
                
                record = self.timestream.create_timestream_record(
                    'shortcut_epic',
                    'everyset_projects',
                    record_data,
                    ts
                )
                records.append(record)
            
            # Fetch iterations
            url = "https://api.app.shortcut.com/api/v3/iterations"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            iterations = response.json()
            for iteration in iterations:
                created_at = datetime.fromisoformat(iteration.get('created_at', '').replace('Z', '+00:00'))
                ts = int(created_at.timestamp() * 1000)
                
                record_data = {
                    'iteration_id': str(iteration.get('id', '')),
                    'name': iteration.get('name', '')[:100],
                    'start_date': iteration.get('start_date', ''),
                    'end_date': iteration.get('end_date', ''),
                    'status': iteration.get('status', ''),
                    'goal': iteration.get('goal', '')[:100],
                    'stats': json.dumps(iteration.get('stats', {}))
                }
                
                record = self.timestream.create_timestream_record(
                    'shortcut_iteration',
                    'everyset_projects',
                    record_data,
                    ts
                )
                records.append(record)
            
            print(f"📊 Processed {len(records)} Shortcut records")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching Shortcut data: {str(e)}")
            return []
    
    def ingest_all_data(self):
        """Ingest data from all sources"""
        print("🚀 Starting data ingestion...")
        print()
        
        # Create database and table
        self.timestream.create_database()
        self.timestream.create_table()
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
        
        # Write all records to Timestream
        if all_records:
            print(f"📝 Writing {len(all_records)} total records to Timestream...")
            self.timestream.write_records(all_records)
            print("✅ Data ingestion completed successfully!")
        else:
            print("⚠️  No data to ingest")
        
        return len(all_records)


def main():
    """Main function to run data ingestion"""
    print("=" * 60)
    print("🕒 TIMESTREAM DATA INGESTION FOR GRAFANA DASHBOARD")
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
    print("1. Configure Grafana to connect to Timestream")
    print("2. Create dashboard queries using the data types:")
    print("   - slack_message")
    print("   - zendesk_ticket") 
    print("   - shortcut_epic")
    print("   - shortcut_iteration")
    print("3. Set up automated ingestion scheduling")


if __name__ == "__main__":
    main()
