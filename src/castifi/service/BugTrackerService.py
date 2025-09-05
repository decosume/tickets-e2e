import logging
from bug_tracker_ingestion import BugTrackerIngestion
from bug_tracker_query import BugTrackerQuery
from bug_tracker_linker import BugTrackerLinker

logger = logging.getLogger()

class BugTrackerService:
    """
    Main service class following the casting pattern.
    Orchestrates bug tracking operations across different systems.
    """
    
    def __init__(self):
        self.ingestion_service = BugTrackerIngestion()
        self.query_service = BugTrackerQuery()
        self.linker_service = BugTrackerLinker()
    
    def run_ingestion(self):
        """Run data ingestion from all sources"""
        try:
            logger.info("Starting bug tracker ingestion")
            
            result = {
                'slack': self.ingestion_service.ingest_slack_data(),
                'zendesk': self.ingestion_service.ingest_zendesk_data(),
                'shortcut': self.ingestion_service.ingest_shortcut_data(),
                'total_processed': 0
            }
            
            # Calculate total processed
            for source, data in result.items():
                if isinstance(data, dict) and 'count' in data:
                    result['total_processed'] += data['count']
            
            logger.info(f"Ingestion completed. Total processed: {result['total_processed']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in ingestion: {str(e)}")
            raise
    
    def query_bugs(self, filters):
        """Query bugs with filters"""
        try:
            logger.info(f"Querying bugs with filters: {filters}")
            
            if filters.get('sourceSystem'):
                result = self.query_service.get_bugs_by_source_system(
                    filters['sourceSystem'], 
                    limit=filters.get('limit', 50)
                )
            elif filters.get('priority'):
                result = self.query_service.get_bugs_by_priority(
                    filters['priority'], 
                    limit=filters.get('limit', 50)
                )
            elif filters.get('state'):
                result = self.query_service.get_bugs_by_state(
                    filters['state'], 
                    limit=filters.get('limit', 50)
                )
            else:
                result = self.query_service.get_all_bugs(
                    limit=filters.get('limit', 50)
                )
            
            logger.info(f"Query completed. Found {result.get('count', 0)} bugs")
            return result
            
        except Exception as e:
            logger.error(f"Error querying bugs: {str(e)}")
            raise
    
    def link_bugs(self, bug_data):
        """Link related bugs across systems"""
        try:
            logger.info("Linking bugs across systems")
            
            result = self.linker_service.link_related_bugs(bug_data)
            
            logger.info(f"Bug linking completed. Linked {result.get('linked_count', 0)} bugs")
            return result
            
        except Exception as e:
            logger.error(f"Error linking bugs: {str(e)}")
            raise
