#!/usr/bin/env python3
"""
Complete database cleanup script.
This will delete ALL records from BugTracker-evt-bugtracker and trigger fresh ingestion.
"""

import boto3
import json
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def get_all_records():
    """Get all records from the table."""
    print("Scanning all records in BugTracker-evt-bugtracker...")
    
    all_items = []
    response = table.scan()
    all_items.extend(response.get('Items', []))
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_items.extend(response.get('Items', []))
    
    print(f"Found {len(all_items)} total records")
    return all_items

def delete_all_records(records):
    """Delete all records in batches."""
    if not records:
        print("No records to delete.")
        return
    
    print(f"\nDeleting {len(records)} records...")
    
    # Delete in batches of 25 (DynamoDB limit)
    batch_size = 25
    deleted_count = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
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
        
        print(f"Deleted batch {i//batch_size + 1}/{(len(records) + batch_size - 1) // batch_size}: {len(batch)} records")
        time.sleep(0.1)  # Small delay to avoid throttling
    
    print(f"\n✅ Successfully deleted {deleted_count} records")

def trigger_complete_ingestion():
    """Trigger complete ingestion for all sources."""
    print("\nTriggering complete ingestion for all sources...")
    
    lambda_client = session.client('lambda', region_name='us-west-2')
    
    try:
        # Create payload for complete ingestion
        payload = {
            'incremental': False,  # Full refresh
            'cleanup_stale': True  # Clean up stale records
        }
        
        response = lambda_client.invoke(
            FunctionName='evt-bugtracker_bug-tracker-ingestion',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Complete ingestion triggered successfully")
        print(f"Response: {result}")
        
    except Exception as e:
        print(f"❌ Error triggering ingestion: {e}")

def verify_cleanup():
    """Verify the cleanup was successful."""
    print("\nVerifying cleanup...")
    
    response = table.scan(Select='COUNT')
    count = response.get('Count', 0)
    
    print(f"Records remaining in table: {count}")
    
    if count == 0:
        print("✅ Database completely cleaned!")
    else:
        print(f"⚠️  {count} records still remain")

def main():
    """Main cleanup process."""
    print("🗑️  COMPLETE DATABASE CLEANUP")
    print("=" * 50)
    print("This will:")
    print("1. Delete ALL records from BugTracker-evt-bugtracker")
    print("2. Trigger fresh ingestion with proper source_system values")
    print("3. Fix the slow dashboard loading issue")
    print()
    
    # Step 1: Get all records
    all_records = get_all_records()
    
    if not all_records:
        print("No records found in table.")
        return
    
    # Show sample records
    print("\n📋 Sample records to be deleted:")
    for i, record in enumerate(all_records[:3]):
        print(f"{i+1}. PK: {record.get('PK', 'N/A')}")
        print(f"   SK: {record.get('SK', 'N/A')}")
        print(f"   source_system: {record.get('source_system', 'null')}")
        print()
    
    # Confirm deletion
    print(f"⚠️  About to delete ALL {len(all_records)} records")
    print("This will completely clean the database and start fresh")
    
    confirm = input("\nProceed with COMPLETE cleanup? (type 'DELETE ALL' to confirm): ").strip()
    
    if confirm == 'DELETE ALL':
        # Delete all records
        delete_all_records(all_records)
        
        # Verify cleanup
        verify_cleanup()
        
        # Wait before re-ingestion
        print("\nWaiting 5 seconds before triggering fresh ingestion...")
        time.sleep(5)
        
        # Trigger fresh ingestion
        trigger_complete_ingestion()
        
        print("\n🎉 COMPLETE CLEANUP AND RE-INGESTION FINISHED!")
        print("The dashboard should now:")
        print("- Load much faster")
        print("- Show proper source distribution (Zendesk > Shortcut > Slack)")
        print("- Only contain properly filtered data")
        
    else:
        print("❌ Cleanup cancelled.")

if __name__ == "__main__":
    main()
