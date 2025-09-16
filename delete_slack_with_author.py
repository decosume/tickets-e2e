#!/usr/bin/env python3
"""
Delete Slack records that contain 'AUTHOR' in their content.
This will remove Slack messages that have the AUTHOR field but are still not legitimate bug reports.
"""

import boto3
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def scan_and_delete_slack_with_author():
    """Delete Slack records that contain 'AUTHOR'."""
    print("🧹 Starting deletion of Slack records WITH 'AUTHOR'...")
    print("This will remove Slack messages that contain 'AUTHOR' field")
    
    deleted_count = 0
    kept_count = 0
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
                
                # Check if it's a Slack record
                if pk.startswith('SL-'):
                    total_slack += 1
                    text = item.get('text', '')
                    
                    # Delete if it contains 'AUTHOR'
                    if 'AUTHOR' in text.upper():
                        batch_items.append(item)
                        
                        # Delete in batches of 25
                        if len(batch_items) >= 25:
                            delete_batch(batch_items)
                            deleted_count += len(batch_items)
                            batch_items = []
                            if deleted_count % 100 == 0:
                                print(f"Deleted {deleted_count} Slack records with 'AUTHOR'...")
                    else:
                        kept_count += 1
            
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
    
    print(f"\n✅ Deletion of AUTHOR Slack records completed!")
    print(f"- Total Slack records found: {total_slack}")
    print(f"- Slack records deleted (had AUTHOR): {deleted_count}")
    print(f"- Slack records kept (no AUTHOR): {kept_count}")
    
    return deleted_count, kept_count

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

def verify_remaining():
    """Check what's left after deletion."""
    print("\n🔍 Checking remaining Slack records...")
    
    try:
        # Quick sample of remaining Slack records
        response = table.scan(
            FilterExpression='begins_with(PK, :pk)',
            ExpressionAttributeValues={':pk': 'SL-'},
            Limit=5
        )
        
        items = response.get('Items', [])
        print(f"Sample of {len(items)} remaining Slack records:")
        
        for i, item in enumerate(items):
            text_preview = item.get('text', '')[:100] + ('...' if len(item.get('text', '')) > 100 else '')
            has_author = 'AUTHOR' in item.get('text', '').upper()
            print(f"{i+1}. PK: {item.get('PK', 'N/A')}")
            print(f"   Text: {text_preview}")
            print(f"   Has AUTHOR: {has_author}")
            print()
            
    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    print("🗑️  DELETE SLACK RECORDS WITH 'AUTHOR'")
    print("=" * 40)
    print("This will DELETE Slack records that contain 'AUTHOR'")
    print("Goal: Remove all Slack messages with AUTHOR field")
    print("Expected result: Much fewer Slack records in dashboard\n")
    
    try:
        deleted_count, kept_count = scan_and_delete_slack_with_author()
        
        verify_remaining()
        
        print(f"\n📊 Expected dashboard results:")
        print(f"- Slack records: {kept_count} (should be much lower)")
        print(f"- Zendesk records: 789")
        print(f"- Shortcut records: 119")
        
        if kept_count < 789:
            print("✅ SUCCESS: Slack should now be much lower than Zendesk!")
        else:
            print("⚠️  There might still be more Slack records to clean")
            
    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")

if __name__ == "__main__":
    main()
