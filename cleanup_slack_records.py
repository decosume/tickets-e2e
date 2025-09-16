#!/usr/bin/env python3
"""
Script to clean up Slack records in DynamoDB that don't contain "AUTHOR" in their text content.
This removes noise from general chat messages that aren't actual bug reports.
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

def filter_records_without_author(records):
    """Filter records that don't contain 'AUTHOR' in their text."""
    records_to_delete = []
    records_to_keep = []
    
    for record in records:
        text = record.get('text', '')
        if 'AUTHOR' not in text.upper():
            records_to_delete.append(record)
        else:
            records_to_keep.append(record)
    
    print(f"Records to delete (no AUTHOR): {len(records_to_delete)}")
    print(f"Records to keep (has AUTHOR): {len(records_to_keep)}")
    
    return records_to_delete, records_to_keep

def show_sample_records(records, title, limit=3):
    """Show sample records for review."""
    print(f"\n=== {title} ===")
    for i, record in enumerate(records[:limit]):
        text_preview = record.get('text', '')[:100] + ('...' if len(record.get('text', '')) > 100 else '')
        print(f"{i+1}. PK: {record.get('PK', 'N/A')}")
        print(f"   Subject: {record.get('subject', 'N/A')}")
        print(f"   Text: {text_preview}")
        print(f"   Channel: {record.get('channel', 'N/A')}")
        print()

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

def main():
    """Main cleanup process."""
    print("🧹 Starting Slack records cleanup...")
    print("This will delete Slack records that don't contain 'AUTHOR' in their text content.\n")
    
    # Step 1: Scan all Slack records
    all_slack_records = scan_slack_records()
    
    if not all_slack_records:
        print("No Slack records found.")
        return
    
    # Step 2: Filter records
    records_to_delete, records_to_keep = filter_records_without_author(all_slack_records)
    
    # Step 3: Show samples for review
    show_sample_records(records_to_delete, "SAMPLE RECORDS TO DELETE (no AUTHOR)")
    show_sample_records(records_to_keep, "SAMPLE RECORDS TO KEEP (has AUTHOR)")
    
    # Step 4: Confirm deletion
    if records_to_delete:
        print(f"\n⚠️  About to delete {len(records_to_delete)} Slack records that don't contain 'AUTHOR'")
        print(f"✅ Will keep {len(records_to_keep)} Slack records that contain 'AUTHOR'")
        
        confirm = input("\nProceed with deletion? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            delete_records_batch(records_to_delete)
            print("\n✅ Cleanup completed successfully!")
        else:
            print("❌ Deletion cancelled.")
    else:
        print("\n✅ No records to delete - all Slack records already contain 'AUTHOR'!")

if __name__ == "__main__":
    main()
