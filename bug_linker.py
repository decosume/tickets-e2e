import os
import boto3
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "BugTracker")

# Initialize AWS DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


class BugLinker:
    def __init__(self):
        self.table = table
    
    def find_bugs_by_source(self, source_system, limit=10):
        """Find bugs from a specific source system"""
        try:
            response = self.table.query(
                IndexName='source-index',
                KeyConditionExpression='sourceSystem = :source_system',
                ExpressionAttributeValues={
                    ':source_system': source_system
                },
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"❌ Error querying bugs by source: {str(e)}")
            return []
    
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
            print(f"❌ Error getting bug details: {str(e)}")
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
                print(f"❌ No records found for ticket ID: {old_ticket_id}")
                return False
            
            print(f"🔗 Linking {len(old_records)} records from {old_ticket_id} to {new_ticket_id}")
            
            # Update each record with the new ticket ID
            for record in old_records:
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
                print(f"  ✅ Updated: {record['SK']}")
            
            print(f"🎯 Successfully linked {len(old_records)} records to {new_ticket_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error linking bugs: {str(e)}")
            return False
    
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
            print(f"❌ No records found for ticket ID: {ticket_id}")
            return
        
        print(f"\n📊 Bug Summary for {ticket_id}:")
        print("=" * 50)
        
        for record in records:
            source = record.get('sourceSystem', 'unknown')
            sk = record.get('SK', '')
            
            if source == 'slack':
                text = record.get('text', 'No text')[:50] + "..."
                print(f"📨 Slack: {text}")
            elif source == 'zendesk':
                subject = record.get('subject', 'No subject')[:50] + "..."
                status = record.get('status', 'unknown')
                print(f"🎫 Zendesk: {subject} (Status: {status})")
            elif source == 'shortcut':
                name = record.get('name', 'No name')[:50] + "..."
                state = record.get('state', 'unknown')
                print(f"📋 Shortcut: {name} (State: {state})")
            
            print(f"  └─ SK: {sk}")
            print(f"  └─ Created: {record.get('createdAt', 'unknown')}")
            print()
    
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
                print("✅ All Slack bugs are linked to Zendesk tickets")
                return []
            
            print(f"\n🔍 Found {len(unlinked_bugs)} unlinked Slack bugs:")
            print("=" * 50)
            
            for bug in unlinked_bugs:
                ticket_id = bug.get('PK', 'unknown')
                text = bug.get('text', 'No text')[:100] + "..."
                created = bug.get('createdAt', 'unknown')
                
                print(f"🎫 {ticket_id}")
                print(f"   Text: {text}")
                print(f"   Created: {created}")
                print()
            
            return unlinked_bugs
            
        except Exception as e:
            print(f"❌ Error listing unlinked Slack bugs: {str(e)}")
            return []


def main():
    """Interactive bug linking utility"""
    print("=" * 60)
    print("🔗 BUG TRACKER LINKING UTILITY")
    print("=" * 60)
    print()
    
    linker = BugLinker()
    
    while True:
        print("\nOptions:")
        print("1. Show bug summary by ticket ID")
        print("2. Link bugs (update ticket ID)")
        print("3. List unlinked Slack bugs")
        print("4. Create synthetic ticket link")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            ticket_id = input("Enter ticket ID (e.g., ZD-12345): ").strip()
            linker.show_bug_summary(ticket_id)
            
        elif choice == "2":
            old_id = input("Enter old ticket ID: ").strip()
            new_id = input("Enter new ticket ID: ").strip()
            linker.link_bugs(old_id, new_id)
            
        elif choice == "3":
            linker.list_unlinked_slack_bugs()
            
        elif choice == "4":
            slack_msg_id = input("Enter Slack message ID: ").strip()
            zendesk_id = input("Enter Zendesk ticket ID: ").strip()
            if not zendesk_id.startswith('ZD-'):
                zendesk_id = f"ZD-{zendesk_id}"
            linker.create_synthetic_ticket(slack_msg_id, zendesk_id)
            
        elif choice == "5":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    main()


