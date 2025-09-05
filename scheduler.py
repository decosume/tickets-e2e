#!/usr/bin/env python3
"""
Automated Data Ingestion Scheduler
Runs the Timestream data ingestion at regular intervals
"""

import schedule
import time
import logging
from datetime import datetime
from dynamodb_data_storage import DataIngestion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_ingestion.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_ingestion():
    """Run the data ingestion process"""
    try:
        logger.info("🚀 Starting scheduled data ingestion...")
        
        # Initialize ingestion
        ingestion = DataIngestion()
        
        # Run ingestion
        total_records = ingestion.ingest_all_data()
        
        logger.info(f"✅ Ingestion completed successfully! {total_records} records processed")
        
        # Log summary
        logger.info(f"📊 Summary: {total_records} records ingested at {datetime.now()}")
        
    except Exception as e:
        logger.error(f"❌ Error during ingestion: {str(e)}")
        raise


def main():
    """Main scheduler function"""
    print("=" * 60)
    print("🕒 AUTOMATED DATA INGESTION SCHEDULER")
    print("=" * 60)
    print()
    
    # Run initial ingestion
    print("🔄 Running initial ingestion...")
    run_ingestion()
    print()
    
    # Schedule regular ingestion
    print("📅 Setting up scheduled ingestion...")
    
    # Schedule every hour
    schedule.every().hour.do(run_ingestion)
    print("✅ Scheduled: Every hour")
    
    # Schedule every 6 hours
    schedule.every(6).hours.do(run_ingestion)
    print("✅ Scheduled: Every 6 hours")
    
    # Schedule daily at 9 AM
    schedule.every().day.at("09:00").do(run_ingestion)
    print("✅ Scheduled: Daily at 9:00 AM")
    
    # Schedule weekly on Monday
    schedule.every().monday.at("08:00").do(run_ingestion)
    print("✅ Scheduled: Every Monday at 8:00 AM")
    
    print()
    print("🔄 Scheduler is running... Press Ctrl+C to stop")
    print("📝 Logs will be saved to 'data_ingestion.log'")
    print()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print()
        print("🛑 Scheduler stopped by user")
        print("📊 Final summary:")
        print("   - Data ingestion completed")
        print("   - Logs saved to 'data_ingestion.log'")
        print("   - Ready for Grafana dashboard")


if __name__ == "__main__":
    main()
