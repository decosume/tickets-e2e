import os
import json
import logging
from castifi.controller.Controller import Controller
from castifi.exceptions.Exceptions import BadRequestException, InternalServerErrorException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main Lambda handler following the casting pattern.
    Routes requests to appropriate controllers based on the event type.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Initialize controller
        controller = Controller()
        
        # Route based on event type
        if 'httpMethod' in event:
            # API Gateway event
            return controller.handle_api_request(event, context)
        elif 'source' in event and event['source'] == 'aws.events':
            # CloudWatch Events (scheduled)
            return controller.handle_scheduled_event(event, context)
        else:
            # Direct invocation or other event types
            return controller.handle_direct_invocation(event, context)
            
    except BadRequestException as e:
        logger.error(f"Bad Request: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': '*'
            },
            'body': json.dumps({
                'error': 'Bad Request',
                'message': str(e)
            })
        }
    except InternalServerErrorException as e:
        logger.error(f"Internal Server Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }

