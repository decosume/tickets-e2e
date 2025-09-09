import json
import logging
from castifi.service.BugTrackerService import BugTrackerService
from castifi.exceptions.Exceptions import BadRequestException, InternalServerErrorException

logger = logging.getLogger()

class Controller:
    """
    Main controller following the casting pattern.
    Handles routing and request/response processing.
    """
    
    def __init__(self):
        self.bug_tracker_service = BugTrackerService()
    
    def handle_api_request(self, event, context):
        """Handle API Gateway requests"""
        try:
            http_method = event.get('httpMethod', '').upper()
            path = event.get('path', '')
            
            logger.info(f"Handling API request: {http_method} {path}")
            
            if path == '/query-bugs' and http_method == 'GET':
                return self._handle_query_bugs(event, context)
            elif path == '/link-bugs' and http_method == 'POST':
                return self._handle_link_bugs(event, context)
            else:
                raise BadRequestException(f"Unsupported endpoint: {http_method} {path}")
                
        except Exception as e:
            logger.error(f"Error handling API request: {str(e)}")
            raise InternalServerErrorException(f"Failed to process API request: {str(e)}")
    
    def handle_scheduled_event(self, event, context):
        """Handle CloudWatch Events (scheduled ingestion)"""
        try:
            logger.info("Handling scheduled ingestion event")
            result = self.bug_tracker_service.run_ingestion()
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Ingestion completed successfully',
                    'result': result
                })
            }
        except Exception as e:
            logger.error(f"Error in scheduled ingestion: {str(e)}")
            raise InternalServerErrorException(f"Scheduled ingestion failed: {str(e)}")
    
    def handle_direct_invocation(self, event, context):
        """Handle direct Lambda invocations"""
        try:
            action = event.get('action', '')
            
            if action == 'ingest':
                result = self.bug_tracker_service.run_ingestion()
            elif action == 'query':
                filters = event.get('filters', {})
                result = self.bug_tracker_service.query_bugs(filters)
            elif action == 'link':
                bug_data = event.get('bug_data', {})
                result = self.bug_tracker_service.link_bugs(bug_data)
            else:
                raise BadRequestException(f"Unsupported action: {action}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Action {action} completed successfully',
                    'result': result
                })
            }
        except Exception as e:
            logger.error(f"Error in direct invocation: {str(e)}")
            raise InternalServerErrorException(f"Direct invocation failed: {str(e)}")
    
    def _handle_query_bugs(self, event, context):
        """Handle GET /query-bugs endpoint"""
        try:
            query_params = event.get('queryStringParameters') or {}
            
            # Extract filters from query parameters
            filters = {
                'sourceSystem': query_params.get('sourceSystem'),
                'priority': query_params.get('priority'),
                'state': query_params.get('state'),
                'limit': int(query_params.get('limit', 50))
            }
            
            result = self.bug_tracker_service.query_bugs(filters)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                'body': json.dumps(result)
            }
        except Exception as e:
            logger.error(f"Error querying bugs: {str(e)}")
            raise InternalServerErrorException(f"Failed to query bugs: {str(e)}")
    
    def _handle_link_bugs(self, event, context):
        """Handle POST /link-bugs endpoint"""
        try:
            body = json.loads(event.get('body', '{}'))
            
            if not body:
                raise BadRequestException("Request body is required")
            
            result = self.bug_tracker_service.link_bugs(body)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                'body': json.dumps(result)
            }
        except json.JSONDecodeError:
            raise BadRequestException("Invalid JSON in request body")
        except Exception as e:
            logger.error(f"Error linking bugs: {str(e)}")
            raise InternalServerErrorException(f"Failed to link bugs: {str(e)}")

