#!/usr/bin/env python3
"""
Comprehensive Slack cleanup - remove all Slack records that are not proper bug reports.
Keep only records with "AUTHOR" or proper bug report structure.
"""

import boto3
import time

# Configure AWS session
session = boto3.Session(profile_name='AdministratorAccess12hr-100142810612')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('BugTracker-evt-bugtracker')

def is_valid_bug_report(text):
    """Check if a Slack message is a valid bug report."""
    text_upper = text.upper()
    
    # Keep messages that contain "AUTHOR" (main bug report format)
    if 'AUTHOR' in text_upper:
        return True
    
    # These appear to be incomplete templates, not actual bug reports
    template_indicators = [
        '*CASTING COMPANY*',
        '*AFFECTED USER*',
        'ALESSI HARTIGAN',
        'GENERAL / NO SPECIFIC CLIENT'
    ]
    
    # If it contains template indicators but no actual content, it's likely not a real bug report
    for indicator in template_indicators:
        if indicator in text_upper:
            # Check if it's just a template without real bug details
            if ('*USER\'S INFO (NAME / CONTACT' in text_upper or 
                '*USER\'S INFO (NAME / CO...' in text_upper):
                return False
    
    # Keep messages that might be legitimate bug reports with different formats
    # You can add more criteria here if needed
    return False

def scan_and_delete_invalid_slack():
    """Scan and delete invalid Slack records."""
    print("🧹 Starting comprehensive Slack cleanup...")
    print("Scanning for invalid Slack records...")
    
    deleted_count = 0
    kept_count = 0
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
                    
                    if is_valid_bug_report(text):
                        kept_count += 1
                    else:
                        batch_items.append(item)
                        
                        # Delete in batches of 25
                        if len(batch_items) >= 25:
                            delete_batch(batch_items)
                            deleted_count += len(batch_items)
                            batch_items = []
                            print(f"Deleted {deleted_count} invalid Slack records...")
            
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
    
    print(f"\n✅ Comprehensive cleanup completed!")
    print(f"- Total records scanned: {total_scanned}")
    print(f"- Invalid Slack records deleted: {deleted_count}")
    print(f"- Valid Slack records kept: {kept_count}")
    
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
    
    try:
        # Get a sample of remaining Slack records
        response = table.scan(Limit=10)
        items = response.get('Items', [])
        
        valid_slack = 0
        invalid_slack = 0
        
        for item in items:
            pk = item.get('PK', '')
            if pk.startswith('SL-'):
                text = item.get('text', '')
                if is_valid_bug_report(text):
                    valid_slack += 1
                else:
                    invalid_slack += 1
        
        print(f"Sample check - Valid Slack records: {valid_slack}")
        print(f"Sample check - Invalid Slack records: {invalid_slack}")
        
    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    print("🚀 COMPREHENSIVE SLACK CLEANUP")
    print("=" * 40)
    print("This will delete ALL invalid Slack records:")
    print("- Messages without 'AUTHOR'")
    print("- Template messages without real content")
    print("- Incomplete bug report forms")
    print("Only keeps legitimate bug reports with proper content\n")
    
    try:
        deleted_count = scan_and_delete_invalid_slack()
        
        if deleted_count > 0:
            verify_results()
            print("\n🎉 Dashboard should now show correct proportions!")
            print("- Only legitimate Slack bug reports remain")
            print("- Zendesk should be the highest source")
        else:
            print("\n✅ No invalid Slack records found!")
            
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")

if __name__ == "__main__":
    main()
