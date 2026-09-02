# Middleware to handle broken pipe and client disconnection errors
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class BrokenPipeMiddleware(MiddlewareMixin):
    """
    Middleware to handle BrokenPipeError and ClientDisconnected errors.
    These occur when the client closes the connection before the server
    finishes sending a response.
    
    This prevents Django from logging these as errors since they're not
    actual server errors - just network disconnections.
    """
    
    def process_exception(self, request, exception):
        """Handle broken pipe and disconnection errors gracefully"""
        
        # Handle broken pipe errors from client disconnections
        if isinstance(exception, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            # Log at warning level instead of error
            logger.warning(
                f"Client disconnected: {type(exception).__name__} - {request.method} {request.path}"
            )
            # Return None to let Django return a generic 500 error without logging as critical
            return None
        
        # Handle other connection errors
        if isinstance(exception, OSError):
            if "broken pipe" in str(exception).lower() or "connection" in str(exception).lower():
                logger.warning(f"Connection error: {exception} - {request.method} {request.path}")
                return None
        
        # Let other exceptions be handled normally
        return None
