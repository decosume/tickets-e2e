#!/usr/bin/env python3
"""
Targeted cleanup script to delete Slack records that don't contain "AUTHOR" in their text content.
This will keep legitimate bug reports and remove noise from general chat messages.
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

def filter_slack_without_author(records):
    """Filter Slack records that don't contain 'AUTHOR' in their text."""
    slack_records_to_delete = []
    slack_records_to_keep = []
    non_slack_records = []
    
    for record in records:
        # Check if it's a Slack record (PK starts with 'SL-')
        pk = record.get('PK', '')
        if pk.startswith('SL-'):
            text = record.get('text', '')
            # Check if 'AUTHOR' is in the text (case insensitive)
            if 'AUTHOR' in text.upper():
                slack_records_to_keep.append(record)
            else:
                slack_records_to_delete.append(record)
        else:
            non_slack_records.append(record)
    
    print(f"\n📊 Record Analysis:")
    print(f"- Slack records WITHOUT 'AUTHOR' (to delete): {len(slack_records_to_delete)}")
    print(f"- Slack records WITH 'AUTHOR' (to keep): {len(slack_records_to_keep)}")
    print(f"- Non-Slack records (untouched): {len(non_slack_records)}")
    
    return slack_records_to_delete, slack_records_to_keep

def show_sample_records(records, title, limit=3):
    """Show sample records for review."""
    print(f"\n=== {title} ===")
    for i, record in enumerate(records[:limit]):
        text_preview = record.get('text', '')[:100] + ('...' if len(record.get('text', '')) > 100 else '')
        print(f"{i+1}. PK: {record.get('PK', 'N/A')}")
        print(f"   Text: {text_preview}")
        print(f"   Has AUTHOR: {'YES' if 'AUTHOR' in record.get('text', '').upper() else 'NO'}")
        print()

def delete_records_batch(records_to_delete):
    """Delete records in batches."""
    if not records_to_delete:
        print("No records to delete.")
        return
    
    print(f"\nDeleting {len(records_to_delete)} Slack records without 'AUTHOR'...")
    
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
        
        print(f"Deleted batch {i//batch_size + 1}/{(len(records_to_delete) + batch_size - 1) // batch_size}: {len(batch)} records")
        time.sleep(0.2)  # Small delay to avoid throttling
    
    print(f"\n✅ Successfully deleted {deleted_count} Slack records without 'AUTHOR'")

def verify_results():
    """Verify the cleanup results."""
    print("\n🔍 Verifying results...")
    
    # Count remaining records
    response = table.scan(Select='COUNT')
    total_count = response.get('Count', 0)
    print(f"Total records remaining: {total_count}")
    
    # Count remaining Slack records
    all_items = []
    response = table.scan()
    all_items.extend(response.get('Items', []))
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_items.extend(response.get('Items', []))
    
    slack_with_author = 0
    slack_without_author = 0
    
    for record in all_items:
        pk = record.get('PK', '')
        if pk.startswith('SL-'):
            text = record.get('text', '')
            if 'AUTHOR' in text.upper():
                slack_with_author += 1
            else:
                slack_without_author += 1
    
    print(f"Remaining Slack records WITH 'AUTHOR': {slack_with_author}")
    print(f"Remaining Slack records WITHOUT 'AUTHOR': {slack_without_author}")
    
    if slack_without_author == 0:
        print("✅ Perfect! All remaining Slack records contain 'AUTHOR'")
    else:
        print(f"⚠️  Still {slack_without_author} Slack records without 'AUTHOR'")

def main():
    """Main cleanup process."""
    print("🧹 TARGETED SLACK CLEANUP")
    print("=" * 40)
    print("This will delete Slack records that don't contain 'AUTHOR' in their text content.")
    print("This keeps legitimate bug reports and removes general chat noise.\n")
    
    # Step 1: Get all records
    all_records = get_all_records()
    
    if not all_records:
        print("No records found in table.")
        return
    
    # Step 2: Filter Slack records
    slack_to_delete, slack_to_keep = filter_slack_without_author(all_records)
    
    # Step 3: Show samples
    if slack_to_delete:
        show_sample_records(slack_to_delete, "SLACK RECORDS TO DELETE (no AUTHOR)")
    
    if slack_to_keep:
        show_sample_records(slack_to_keep, "SLACK RECORDS TO KEEP (has AUTHOR)")
    
    # Step 4: Confirm deletion
    if slack_to_delete:
        print(f"\n⚠️  About to delete {len(slack_to_delete)} Slack records without 'AUTHOR'")
        print(f"✅ Will keep {len(slack_to_keep)} Slack records with 'AUTHOR'")
        print(f"✅ Will keep all {len(all_records) - len(slack_to_delete) - len(slack_to_keep)} non-Slack records")
        
        confirm = input("\nProceed with Slack cleanup? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            delete_records_batch(slack_to_delete)
            verify_results()
            
            print("\n🎉 SLACK CLEANUP COMPLETED!")
            print("The dashboard should now show:")
            print("- Much fewer Slack records (only bug reports)")
            print("- Zendesk as the highest source")
            print("- Faster loading due to less data")
            
        else:
            print("❌ Cleanup cancelled.")
    else:
        print("\n✅ No Slack records without 'AUTHOR' found!")
        print("All Slack records already contain 'AUTHOR' - no cleanup needed.")

if __name__ == "__main__":
    main()
