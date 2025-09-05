import os
import re
import boto3
import json
import time
import logging
from datetime import datetime
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'BugTracker')
table = dynamodb.Table(table_name)

# API Configuration from environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")
ZENDESK_SUBDOMAIN = os.environ.get("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.environ.get("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.environ.get("ZENDESK_API_TOKEN")
SHORTCUT_API_TOKEN = os.environ.get("SHORTCUT_API_TOKEN")


class BugTrackerIngestion:
    def __init__(self):
        self.table = table
        self.ingestion_count = 0
    
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
            self.ingestion_count += 1
            logger.info(f"Upserted [{ticket_id}] from [{source_system}] → {attributes.get('subject', attributes.get('text', attributes.get('name', 'No title')))}")
            
        except Exception as e:
            logger.error(f"Error upserting item: {str(e)}")
            raise
    
    def extract_ticket_info_from_slack(self, text):
        """Extract ticketId and priority if available, fallback if not."""
        ticket_pattern = re.search(r"ticketId[:=]\s*(\S+)", text, re.IGNORECASE)
        priority_pattern = re.search(r"priority[:=]\s*(\S+)", text, re.IGNORECASE)

        ticket_id = ticket_pattern.group(1) if ticket_pattern else f"SL-{hash(text)}"
        priority = priority_pattern.group(1).capitalize() if priority_pattern else "Unknown"

        return ticket_id, priority
    
    def fetch_slack_messages(self):
        """Fetch Slack messages and normalize into bug records."""
        logger.info("Fetching Slack messages...")
        
        if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
            logger.warning("Slack configuration missing, skipping Slack ingestion")
            return []
        
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
                
                self.upsert_bug_item(ticket_id, "slack", msg_id, bug_data)
                results.append((ticket_id, bug_data))

            logger.info(f"Processed {len(results)} Slack records")
            return results

        except Exception as e:
            logger.error(f"Error fetching Slack messages: {str(e)}")
            return []
    
    def fetch_zendesk_tickets(self):
        """Fetch Zendesk tickets and normalize into bug records."""
        logger.info("Fetching Zendesk tickets...")
        
        if not ZENDESK_SUBDOMAIN or not ZENDESK_EMAIL or not ZENDESK_API_TOKEN:
            logger.warning("Zendesk configuration missing, skipping Zendesk ingestion")
            return []
        
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
                
                self.upsert_bug_item(ticket_id, "zendesk", str(t['id']), bug_data)
                results.append((ticket_id, bug_data))

            logger.info(f"Processed {len(results)} Zendesk records")
            return results

        except Exception as e:
            logger.error(f"Error fetching Zendesk tickets: {str(e)}")
            return []
    
    def fetch_shortcut_bugs(self):
        """Fetch Shortcut bugs and normalize into bug records."""
        logger.info("Fetching Shortcut bugs...")
        
        if not SHORTCUT_API_TOKEN:
            logger.warning("Shortcut configuration missing, skipping Shortcut ingestion")
            return []
        
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
                
                self.upsert_bug_item(ticket_id, "shortcut", str(bug['id']), bug_data)
                results.append((ticket_id, bug_data))

            logger.info(f"Processed {len(results)} Shortcut records")
            return results

        except Exception as e:
            logger.error(f"Error fetching Shortcut bugs: {str(e)}")
            return []
    
    def ingest_all_data(self):
        """Ingest data from all sources using the unified schema"""
        logger.info("Starting BugTracker data ingestion...")
        
        # Fetch data from all sources
        slack_records = self.fetch_slack_messages()
        zendesk_records = self.fetch_zendesk_tickets()
        shortcut_records = self.fetch_shortcut_bugs()
        
        total_records = len(slack_records) + len(zendesk_records) + len(shortcut_records)
        logger.info(f"Ingestion complete. Total records processed: {total_records}")
        
        return {
            'total_records': total_records,
            'slack_records': len(slack_records),
            'zendesk_records': len(zendesk_records),
            'shortcut_records': len(shortcut_records),
            'ingestion_count': self.ingestion_count
        }


def lambda_handler(event, context):
    """
    Lambda handler for BugTracker data ingestion
    """
    try:
        ingestion = BugTrackerIngestion()
        result = ingestion.ingest_all_data()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'BugTracker ingestion completed successfully',
                'result': result
            })
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


