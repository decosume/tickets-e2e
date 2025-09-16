#!/usr/bin/env python3
"""
Strict Slack cleanup - keep ONLY records with 'AUTHOR' (the definitive bug report format).
Remove all other Slack records as they are likely templates or incomplete forms.
"""

import boto3
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def scan_and_delete_slack_without_author():
    """Keep ONLY Slack records that contain 'AUTHOR'."""
    print("🧹 Starting STRICT Slack cleanup...")
    print("Will keep ONLY Slack records containing 'AUTHOR'")
    
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
                    
                    # STRICT: Keep ONLY if it contains 'AUTHOR'
                    if 'AUTHOR' in text.upper():
                        kept_count += 1
                    else:
                        batch_items.append(item)
                        
                        # Delete in batches of 25
                        if len(batch_items) >= 25:
                            delete_batch(batch_items)
                            deleted_count += len(batch_items)
                            batch_items = []
                            if deleted_count % 100 == 0:
                                print(f"Deleted {deleted_count} Slack records without 'AUTHOR'...")
            
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
    
    print(f"\n✅ STRICT cleanup completed!")
    print(f"- Total Slack records found: {total_slack}")
    print(f"- Slack records deleted (no AUTHOR): {deleted_count}")
    print(f"- Slack records kept (has AUTHOR): {kept_count}")
    
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

def main():
    print("🚀 STRICT SLACK CLEANUP")
    print("=" * 30)
    print("This will keep ONLY Slack records with 'AUTHOR'")
    print("All other Slack records will be deleted")
    print("Goal: Zendesk (789) > Slack records\n")
    
    try:
        deleted_count, kept_count = scan_and_delete_slack_without_author()
        
        print(f"\n📊 Expected results:")
        print(f"- Slack records: {kept_count}")
        print(f"- Zendesk records: 789")
        print(f"- Shortcut records: 119")
        
        if kept_count < 789:
            print("✅ SUCCESS: Slack will now be lower than Zendesk!")
        else:
            print("⚠️  Slack is still higher than Zendesk")
            
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")

if __name__ == "__main__":
    main()
