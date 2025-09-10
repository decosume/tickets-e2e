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
        """Extract ticketId, priority, status, and other fields from Slack text."""
        ticket_pattern = re.search(r"ticketId[:=]\s*(\S+)", text, re.IGNORECASE)
        priority_pattern = re.search(r"priority[:=]\s*(\S+)", text, re.IGNORECASE)
        status_pattern = re.search(r"status[:=]\s*(\S+)", text, re.IGNORECASE)
        state_pattern = re.search(r"state[:=]\s*(\S+)", text, re.IGNORECASE)
        assignee_pattern = re.search(r"assignee[:=]\s*(\S+)", text, re.IGNORECASE)
        
        # Extract subject from first line or before first newline
        subject = text.split('\n')[0][:100] if text else "Slack Message"
        
        ticket_id = ticket_pattern.group(1) if ticket_pattern else f"SL-{abs(hash(text))}"
        priority = priority_pattern.group(1).capitalize() if priority_pattern else "Medium"
        status = status_pattern.group(1).capitalize() if status_pattern else "Open"
        state = state_pattern.group(1).capitalize() if state_pattern else "open"
        assignee = assignee_pattern.group(1) if assignee_pattern else None

        return {
            'ticket_id': ticket_id,
            'priority': priority,
            'status': status,
            'state': state,
            'subject': subject,
            'assignee': assignee
        }
    
    def fetch_slack_messages(self):
        """Fetch Slack messages from multiple channels and normalize into bug records."""
        logger.info("Fetching Slack messages from multiple channels...")
        
        if not SLACK_BOT_TOKEN:
            logger.warning("Slack bot token missing, skipping Slack ingestion")
            return []
        
        # Define channels to monitor for bug reports
        # Format: [(channel_id, channel_name), ...]
        channels_to_monitor = [
            ("C08LC7Q97FY", "urgent-vouchers"),          # Current primary channel
            ("C0921KTEKNG", "urgent-casting-platform"),  # Additional channel 1
            ("C08LHAYC9L5", "urgent-casting"),           # Additional channel 2  
            ("C01AAB3S8TU", "product-vouchers")          # Additional channel 3
        ]
        
        # Fallback to single channel if configured (for backward compatibility)
        if SLACK_CHANNEL_ID and not any(ch[0] == SLACK_CHANNEL_ID for ch in channels_to_monitor):
            channels_to_monitor.append((SLACK_CHANNEL_ID, "configured-channel"))
        
        all_results = []
        
        for channel_id, channel_name in channels_to_monitor:
            try:
                logger.info(f"Fetching messages from #{channel_name} ({channel_id})")
                
                url = "https://slack.com/api/conversations.history"
                headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
                params = {"channel": channel_id, "limit": 50}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                if not data.get("ok"):
                    logger.warning(f"Slack API error for #{channel_name}: {data.get('error', 'Unknown error')}")
                    continue
                    
                messages = data.get("messages", [])
                channel_results = []

                for msg in messages:
                    text = msg.get("text", "")
                    extracted_info = self.extract_ticket_info_from_slack(text)
                    msg_id = msg.get("ts", str(time.time()))
                    
                    # Include channel information in the ticket ID and bug data
                    channel_suffix = f"#{channel_name}"
                    ticket_id_with_channel = f"{extracted_info['ticket_id']}-{channel_id}"

                    bug_data = {
                        "author": msg.get("user", "unknown"),
                        "text": text,
                        "priority": extracted_info['priority'],
                        "status": extracted_info['status'],
                        "state": extracted_info['state'],
                        "subject": f"{extracted_info['subject']} ({channel_suffix})",
                        "assignee": extracted_info['assignee'],
                        "channel": channel_name,
                        "channel_id": channel_id,
                        "createdAt": datetime.fromtimestamp(float(msg["ts"])).isoformat(),
                        "sourceUpdatedAt": datetime.fromtimestamp(float(msg["ts"])).isoformat(),  # Slack messages don't change
                        "syncedAt": datetime.now().isoformat()   # Track when we synced this record
                    }
                    
                    self.upsert_bug_item(ticket_id_with_channel, "slack", f"{channel_id}#{msg_id}", bug_data)
                    channel_results.append((ticket_id_with_channel, bug_data))

                logger.info(f"Processed {len(channel_results)} messages from #{channel_name}")
                all_results.extend(channel_results)

            except Exception as e:
                logger.error(f"Error fetching messages from #{channel_name} ({channel_id}): {str(e)}")
                continue

        logger.info(f"Total Slack records processed: {len(all_results)} from {len(channels_to_monitor)} channels")
        return all_results
    
    def fetch_zendesk_tickets(self):
        """Fetch ALL Zendesk tickets and normalize into bug records with proper state sync."""
        logger.info("Fetching ALL Zendesk tickets for complete state synchronization...")
        
        if not ZENDESK_SUBDOMAIN or not ZENDESK_EMAIL or not ZENDESK_API_TOKEN:
            logger.warning("Zendesk configuration missing, skipping Zendesk ingestion")
            return []
        
        try:
            all_tickets = []
            page_num = 1
            
            while True:
                # Fetch ALL tickets regardless of status for complete sync
                # Use pagination to handle large datasets
                url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json?page={page_num}&per_page=100"
                auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
                response = requests.get(url, auth=auth, timeout=10)
                response.raise_for_status()

                data = response.json()
                tickets = data.get("tickets", [])
                
                if not tickets:  # No more tickets to fetch
                    break
                    
                all_tickets.extend(tickets)
                page_num += 1
                
                # Safety limit to prevent infinite loops
                if page_num > 50:
                    logger.warning("Reached page limit (50), stopping pagination")
                    break

            results = []
            closed_count = 0
            active_count = 0

            for t in all_tickets:
                ticket_id = f"ZD-{t['id']}"
                ticket_status = t.get("status", "").lower()
                
                # Map Zendesk status to our normalized state
                state_mapping = {
                    "new": "open",
                    "open": "open", 
                    "pending": "pending",
                    "hold": "pending",
                    "solved": "closed",
                    "closed": "closed"
                }
                
                normalized_state = state_mapping.get(ticket_status, ticket_status)
                
                # Track counts for logging
                if normalized_state == "closed":
                    closed_count += 1
                else:
                    active_count += 1

                bug_data = {
                    "requester": t.get("requester_id"),
                    "assignee": t.get("assignee_id"),
                    "priority": t.get("priority") or "Medium",
                    "status": t.get("status") or "Open",
                    "state": normalized_state,
                    "subject": t.get("subject") or "Zendesk Ticket",
                    "text": t.get("description") or "",
                    "author": str(t.get("requester_id")) if t.get("requester_id") else "unknown",
                    "createdAt": t.get("created_at"),
                    "updatedAt": t.get("updated_at"),
                    "sourceUpdatedAt": t.get("updated_at"),  # Track source system updates
                    "syncedAt": datetime.now().isoformat()   # Track when we synced this record
                }
                
                self.upsert_bug_item(ticket_id, "zendesk", str(t['id']), bug_data)
                results.append((ticket_id, bug_data))

            logger.info(f"Processed {len(results)} total Zendesk tickets: {active_count} active, {closed_count} closed")
            return results

        except Exception as e:
            logger.error(f"Error fetching Zendesk tickets: {str(e)}")
            return []
    
    def fetch_shortcut_users(self):
        """Fetch Shortcut users for name mapping"""
        logger.info("Fetching Shortcut users for owner name mapping...")
        
        if not SHORTCUT_API_TOKEN:
            return {}
            
        try:
            url = "https://api.app.shortcut.com/api/v3/members"
            headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            users = response.json()
            user_map = {}
            
            for user in users:
                user_id = str(user.get("id", ""))
                name = user.get("profile", {}).get("name") or user.get("profile", {}).get("display_name") or f"User {user_id}"
                user_map[user_id] = name
                
            logger.info(f"Loaded {len(user_map)} Shortcut users for name mapping")
            return user_map
            
        except Exception as e:
            logger.error(f"Error fetching Shortcut users: {str(e)}")
            return {}

    def fetch_shortcut_bugs(self):
        """Fetch ALL Shortcut bug stories and normalize into bug records with proper state sync."""
        logger.info("Fetching ALL Shortcut bug stories for complete state synchronization...")
        
        if not SHORTCUT_API_TOKEN:
            logger.warning("Shortcut configuration missing, skipping Shortcut ingestion")
            return []
        
        try:
            # First, get user mapping for owner names
            user_map = self.fetch_shortcut_users()
            all_bugs = []
            page_size = 25
            next_token = None
            
            while True:
                # Fetch ALL bug stories regardless of completion status
                query = "type:bug"  # Removed state restrictions for complete sync
                
                url = "https://api.app.shortcut.com/api/v3/search/stories"
                headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
                params = {"query": query, "page_size": page_size}
                
                if next_token:
                    params["next"] = next_token
                    
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                bugs = data.get("data", [])
                
                if not bugs:  # No more stories to fetch
                    break
                    
                all_bugs.extend(bugs)
                next_token = data.get("next")
                
                if not next_token:  # No more pages
                    break
                    
                # Safety limit to prevent infinite loops
                if len(all_bugs) > 1000:
                    logger.warning("Reached story limit (1000), stopping pagination")
                    break

            results = []
            completed_count = 0
            active_count = 0

            for bug in all_bugs:
                ticket_id = None
                if bug.get("name") and "ZD-" in bug["name"]:  # try to extract Zendesk ID
                    match = re.search(r"(ZD-\d+)", bug["name"])
                    if match:
                        ticket_id = match.group(1)

                if not ticket_id:
                    ticket_id = f"SC-{bug['id']}"

                # Enhanced workflow state mapping with completion detection
                workflow_state_id = bug.get('workflow_state_id')
                completed = bug.get("completed", False)
                archived = bug.get("archived", False)
                
                # Map workflow state ID to readable name and normalized state
                workflow_mapping = {
                    "500000027": {"name": "Ready for Dev", "state": "open"},
                    "500000043": {"name": "In Progress", "state": "in_progress"}, 
                    "500000385": {"name": "Code Review", "state": "in_progress"},
                    "500003719": {"name": "Ready for QA", "state": "in_progress"},
                    "500009065": {"name": "Blocked", "state": "blocked"},
                    "500000028": {"name": "Done", "state": "closed"},
                    "500000380": {"name": "To Do", "state": "open"},
                    "500008605": {"name": "QA Testing", "state": "in_progress"},
                    "500000042": {"name": "Needs Review", "state": "pending"}
                }
                
                workflow_info = workflow_mapping.get(workflow_state_id, {
                    "name": f"Unknown ({workflow_state_id})", 
                    "state": "unknown"
                })
                
                status_name = workflow_info["name"]
                normalized_state = workflow_info["state"]
                
                # Override state based on completion status
                if completed or archived:
                    status_name = "Complete"
                    normalized_state = "closed"
                    completed_count += 1
                else:
                    active_count += 1

                # Extract priority from Shortcut story
                priority = "Medium"  # Default
                if bug.get("priority"):
                    # Map Shortcut priority to readable names
                    priority_mapping = {
                        "high": "High",
                        "medium": "Medium", 
                        "low": "Low",
                        "critical": "Critical"
                    }
                    priority = priority_mapping.get(bug.get("priority", "").lower(), bug.get("priority", "Medium"))
                elif bug.get("story_type") == "bug":
                    priority = "High"  # Fallback for bugs without explicit priority
                
                # Extract assignee info (map owner ID to name)
                assignee = "Unassigned"
                if bug.get("owner_ids") and len(bug["owner_ids"]) > 0:
                    owner_id = str(bug["owner_ids"][0])
                    assignee = user_map.get(owner_id, f"User {owner_id}")

                bug_data = {
                    "shortcut_story_id": bug["id"],
                    "name": bug.get("name", ""),
                    "subject": bug.get("name", "Shortcut Bug"),
                    "text": bug.get("description", ""),
                    "priority": priority,
                    "status": normalized_state,  # Show state in Status column (e.g., "in_progress")
                    "state": normalized_state,
                    "workflow_status": status_name,  # Keep the original workflow status as separate field
                    "assignee": assignee,
                    "author": str(bug.get("requester_id", "unknown")),
                    "createdAt": bug.get("created_at"),
                    "updatedAt": bug.get("updated_at"),
                    "sourceUpdatedAt": bug.get("updated_at"),  # Track source system updates
                    "syncedAt": datetime.now().isoformat(),   # Track when we synced this record
                    "completed": completed,
                    "archived": archived,
                    "workflow_state_id": workflow_state_id
                }
                
                self.upsert_bug_item(ticket_id, "shortcut", str(bug['id']), bug_data)
                results.append((ticket_id, bug_data))

            logger.info(f"Processed {len(results)} total Shortcut stories: {active_count} active, {completed_count} completed")
            return results

        except Exception as e:
            logger.error(f"Error fetching Shortcut bugs: {str(e)}")
            return []
    
    def cleanup_stale_records(self, cutoff_hours=24):
        """Mark records as stale if they haven't been synced recently"""
        logger.info(f"Checking for stale records older than {cutoff_hours} hours...")
        
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=cutoff_hours)
            cutoff_iso = cutoff_time.isoformat()
            
            # Scan for records that haven't been synced recently
            response = self.table.scan(
                FilterExpression='attribute_not_exists(syncedAt) OR syncedAt < :cutoff',
                ExpressionAttributeValues={':cutoff': cutoff_iso}
            )
            
            stale_records = response.get('Items', [])
            
            if stale_records:
                logger.info(f"Found {len(stale_records)} potentially stale records")
                # For now, just log them. In the future, we could mark them as stale or delete them
                for record in stale_records[:5]:  # Log first 5 as examples
                    pk = record.get('PK', 'Unknown')
                    sk = record.get('SK', 'Unknown')
                    last_sync = record.get('syncedAt', 'Never')
                    logger.info(f"Stale record: {pk}#{sk} last synced: {last_sync}")
            else:
                logger.info("No stale records found")
                
            return len(stale_records)
            
        except Exception as e:
            logger.error(f"Error during stale record cleanup: {str(e)}")
            return 0

    def ingest_all_data(self):
        """Ingest data from all sources using the unified schema with state synchronization"""
        logger.info("Starting BugTracker data ingestion with comprehensive state synchronization...")
        
        # Perform comprehensive ingestion from all sources
        slack_records = self.fetch_slack_messages()
        zendesk_records = self.fetch_zendesk_tickets()
        shortcut_records = self.fetch_shortcut_bugs()
        
        # Cleanup stale records that weren't updated in this sync
        stale_count = self.cleanup_stale_records()
        
        total_records = len(slack_records) + len(zendesk_records) + len(shortcut_records)
        logger.info(f"Ingestion complete. Total records processed: {total_records}, Stale records: {stale_count}")
        
        return {
            'message': 'BugTracker ingestion completed with full state synchronization',
            'total_records': total_records,
            'slack_records': len(slack_records),
            'zendesk_records': len(zendesk_records),
            'shortcut_records': len(shortcut_records),
            'stale_records': stale_count,
            'ingestion_count': self.ingestion_count
        }


def lambda_handler(event, context):
    """
    Lambda handler for BugTracker data ingestion with enhanced sync options
    
    Event parameters:
    - incremental: bool - If true, only sync records updated since last sync
    - source: str - Specific source to sync (slack, zendesk, shortcut)
    - cleanup_stale: bool - If true, identify stale records (default: true)
    """
    try:
        ingestion = BugTrackerIngestion()
        
        # Parse event parameters
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                params = json.loads(body)
            except:
                params = {}
        else:
            params = body or {}
            
        # Extract sync parameters
        incremental = params.get('incremental', False)
        source_filter = params.get('source')
        cleanup_stale = params.get('cleanup_stale', True)
        
        logger.info(f"Starting ingestion with params: incremental={incremental}, source={source_filter}, cleanup_stale={cleanup_stale}")
        
        # Perform targeted ingestion based on parameters
        slack_records = []
        zendesk_records = []
        shortcut_records = []
        
        if not source_filter or source_filter == 'slack':
            slack_records = ingestion.fetch_slack_messages()
            
        if not source_filter or source_filter == 'zendesk':
            zendesk_records = ingestion.fetch_zendesk_tickets()
            
        if not source_filter or source_filter == 'shortcut':
            shortcut_records = ingestion.fetch_shortcut_bugs()
        
        # Cleanup stale records if requested
        stale_count = 0
        if cleanup_stale:
            stale_count = ingestion.cleanup_stale_records()
        
        total_records = len(slack_records) + len(zendesk_records) + len(shortcut_records)
        
        result = {
            'message': 'BugTracker ingestion completed with full state synchronization',
            'total_records': total_records,
            'slack_records': len(slack_records),
            'zendesk_records': len(zendesk_records),
            'shortcut_records': len(shortcut_records),
            'stale_records': stale_count,
            'ingestion_count': ingestion.ingestion_count,
            'parameters': {
                'incremental': incremental,
                'source_filter': source_filter,
                'cleanup_stale': cleanup_stale
            }
        }
        
        logger.info(f"Ingestion summary: {result}")
        
        return {
            'statusCode': 200,
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


