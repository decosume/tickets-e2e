#!/usr/bin/env python3
"""
Automatic cleanup script to delete Slack records without 'AUTHOR'.
No user input required - runs automatically.
"""

import boto3
import time
import sys

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def scan_and_delete_slack_without_author():
    """Scan and delete Slack records without AUTHOR in one pass."""
    print("🧹 Starting automatic Slack cleanup...")
    print("Scanning for Slack records without 'AUTHOR'...")
    
    deleted_count = 0
    total_scanned = 0
    batch_items = []
    
    # Scan the table in chunks
    paginator = table.scan()
    
    while True:
        try:
            # Process current page
            items = paginator.get('Items', [])
            total_scanned += len(items)
            
            for item in items:
                pk = item.get('PK', '')
                
                # Check if it's a Slack record
                if pk.startswith('SL-'):
                    text = item.get('text', '')
                    
                    # Check if it does NOT contain 'AUTHOR'
                    if 'AUTHOR' not in text.upper():
                        batch_items.append(item)
                        
                        # Delete in batches of 25
                        if len(batch_items) >= 25:
                            delete_batch(batch_items)
                            deleted_count += len(batch_items)
                            batch_items = []
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
    
    print(f"\n✅ Cleanup completed!")
    print(f"- Total records scanned: {total_scanned}")
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
        time.sleep(0.1)  # Small delay to avoid throttling
    except Exception as e:
        print(f"Error deleting batch: {e}")

def verify_results():
    """Quick verification of results."""
    print("\n🔍 Verifying results...")
    
    slack_with_author = 0
    slack_without_author = 0
    
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # Process first page only for quick check
        for item in items:
            pk = item.get('PK', '')
            if pk.startswith('SL-'):
                text = item.get('text', '')
                if 'AUTHOR' in text.upper():
                    slack_with_author += 1
                else:
                    slack_without_author += 1
        
        print(f"Sample check - Slack with AUTHOR: {slack_with_author}")
        print(f"Sample check - Slack without AUTHOR: {slack_without_author}")
        
    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    print("🚀 AUTOMATIC SLACK CLEANUP STARTING...")
    print("This will delete Slack records that don't contain 'AUTHOR'")
    print("No confirmation required - running automatically\n")
    
    try:
        deleted_count = scan_and_delete_slack_without_author()
        
        if deleted_count > 0:
            verify_results()
            print("\n🎉 Dashboard should now show correct proportions!")
            print("- Fewer Slack records (only bug reports)")
            print("- Zendesk should be the highest source")
        else:
            print("\n✅ No Slack records without 'AUTHOR' found!")
            
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
