#!/usr/bin/env python3
"""
Script to clean up ALL Slack records in DynamoDB and re-ingest with proper AUTHOR filtering.
This will remove all the duplicate and non-bug-report Slack messages.
"""

import boto3
import json
from decimal import Decimal
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def scan_slack_records():
    """Scan for all Slack records in the table."""
    print("Scanning for Slack records...")
    
    response = table.scan(
        FilterExpression='source_system = :source',
        ExpressionAttributeValues={':source': 'slack'}
    )
    
    items = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='source_system = :source',
            ExpressionAttributeValues={':source': 'slack'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    
    print(f"Found {len(items)} Slack records total")
    return items

def delete_records_batch(records_to_delete):
    """Delete records in batches."""
    if not records_to_delete:
        print("No records to delete.")
        return
    
    print(f"\nDeleting {len(records_to_delete)} records...")
    
    # Delete in batches of 25 (DynamoDB limit)
    batch_size = 25
    deleted_count = 0
    
    for i in range(0, len(records_to_delete), batch_size):
        batch = records_to_delete[i:i + batch_size]
        
        with table.batch_writer() as batch_writer:
            for record in batch:
                try:
                    batch_writer.delete_item(
                        Key={
                            'PK': record['PK'],
                            'SK': record['SK']
                        }
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting record {record.get('PK', 'unknown')}: {e}")
        
        print(f"Deleted batch {i//batch_size + 1}: {len(batch)} records")
        time.sleep(0.1)  # Small delay to avoid throttling
    
    print(f"\nSuccessfully deleted {deleted_count} records")

def trigger_fresh_ingestion():
    """Trigger a fresh Slack ingestion with the new AUTHOR filter."""
    print("\nTriggering fresh Slack ingestion...")
    
    lambda_client = session.client('lambda', region_name='us-west-2')
    
    try:
        response = lambda_client.invoke(
            FunctionName='evt-bugtracker_bug-tracker-ingestion',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'source': 'slack',  # Only ingest Slack
                'incremental': False  # Full refresh
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Ingestion triggered successfully: {result}")
        
    except Exception as e:
        print(f"❌ Error triggering ingestion: {e}")

def main():
    """Main cleanup process."""
    print("🧹 Starting COMPLETE Slack records cleanup...")
    print("This will delete ALL Slack records and re-ingest with proper AUTHOR filtering.\n")
    
    # Step 1: Scan all Slack records
    all_slack_records = scan_slack_records()
    
    if not all_slack_records:
        print("No Slack records found.")
        return
    
    # Step 2: Show sample for review
    print(f"\n📋 Sample records to be deleted:")
    for i, record in enumerate(all_slack_records[:3]):
        text_preview = record.get('text', '')[:100] + ('...' if len(record.get('text', '')) > 100 else '')
        print(f"{i+1}. PK: {record.get('PK', 'N/A')}")
        print(f"   Subject: {record.get('subject', 'N/A')}")
        print(f"   Text: {text_preview}")
        print()
    
    # Step 3: Confirm deletion
    print(f"\n⚠️  About to delete ALL {len(all_slack_records)} Slack records")
    print("Then trigger fresh ingestion with AUTHOR filter")
    
    confirm = input("\nProceed with complete cleanup? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        # Delete all Slack records
        delete_records_batch(all_slack_records)
        
        # Wait a moment
        print("\nWaiting 3 seconds before re-ingestion...")
        time.sleep(3)
        
        # Trigger fresh ingestion
        trigger_fresh_ingestion()
        
        print("\n✅ Complete cleanup and re-ingestion completed!")
        print("The dashboard should now load much faster with only proper bug reports.")
    else:
        print("❌ Cleanup cancelled.")

if __name__ == "__main__":
    main()
