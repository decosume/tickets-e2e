class BugTrackerException(Exception):
    """Base exception for BugTracker service"""
    pass

class BadRequestException(BugTrackerException):
    """Exception for bad requests (400)"""
    pass

class InternalServerErrorException(BugTrackerException):
    """Exception for internal server errors (500)"""
    pass

class DataIngestionException(BugTrackerException):
    """Exception for data ingestion errors"""
    pass

class DatabaseException(BugTrackerException):
    """Exception for database operation errors"""
    pass

class ExternalApiException(BugTrackerException):
    """Exception for external API errors"""
    pass
