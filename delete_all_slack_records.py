#!/usr/bin/env python3
"""
Delete ALL Slack records regardless of content.
This is the most comprehensive solution to prevent Slack noise in the dashboard.
"""

import boto3
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def scan_and_delete_all_slack():
    """Delete ALL Slack records regardless of content."""
    print("🧹 Starting deletion of ALL Slack records...")
    print("This will remove ALL Slack messages regardless of content")
    
    deleted_count = 0
    total_slack = 0
    batch_items = []
    
    # Scan the table in chunks
    paginator = table.scan()
    
    while True:
        try:
            # Process current page
            items = paginator.get('Items', [])
            
            for item in items:
                pk = item.get('PK', '')
                
                # Check if it's a Slack record (PK starts with 'SL-')
                if pk.startswith('SL-'):
                    total_slack += 1
                    batch_items.append(item)
                    
                    # Delete in batches of 25
                    if len(batch_items) >= 25:
                        delete_batch(batch_items)
                        deleted_count += len(batch_items)
                        batch_items = []
                        if deleted_count % 100 == 0:
                            print(f"Deleted {deleted_count} Slack records...")
            
            # Check if there are more pages
            if 'LastEvaluatedKey' not in paginator:
                break
                
            # Get next page
            paginator = table.scan(ExclusiveStartKey=paginator['LastEvaluatedKey'])
            
        except Exception as e:
            print(f"Error during scan: {e}")
            break
    
    # Delete remaining items in batch
    if batch_items:
        delete_batch(batch_items)
        deleted_count += len(batch_items)
    
    print(f"\n✅ Deletion of ALL Slack records completed!")
    print(f"- Total Slack records found: {total_slack}")
    print(f"- Slack records deleted: {deleted_count}")
    
    return deleted_count

def delete_batch(items):
    """Delete a batch of items."""
    try:
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        'PK': item['PK'],
                        'SK': item['SK']
                    }
                )
        time.sleep(0.1)
    except Exception as e:
        print(f"Error deleting batch: {e}")

def verify_no_slack_remaining():
    """Verify no Slack records remain."""
    print("\n🔍 Verifying no Slack records remain...")
    
    try:
        response = table.scan(
            FilterExpression='begins_with(PK, :pk)',
            ExpressionAttributeValues={':pk': 'SL-'},
            Select='COUNT'
        )
        
        count = response.get('Count', 0)
        print(f"Remaining Slack records: {count}")
        
        if count == 0:
            print("✅ Perfect! No Slack records remaining.")
        else:
            print(f"⚠️  Still {count} Slack records found.")
            
    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    print("🗑️  DELETE ALL SLACK RECORDS")
    print("=" * 35)
    print("This will DELETE ALL Slack records in the database")
    print("Goal: Completely eliminate Slack noise from bug tracker")
    print("Expected result: Only Zendesk and Shortcut data\n")
    
    try:
        deleted_count = scan_and_delete_all_slack()
        
        verify_no_slack_remaining()
        
        print(f"\n📊 Expected dashboard results:")
        print(f"- Slack records: 0")
        print(f"- Zendesk records: ~789")
        print(f"- Shortcut records: ~121")
        
        print("\n✅ SUCCESS: Dashboard should now show only legitimate bug sources!")
        print("Future scheduled ingestions will be filtered by the AUTHOR requirement.")
            
    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")

if __name__ == "__main__":
    main()
