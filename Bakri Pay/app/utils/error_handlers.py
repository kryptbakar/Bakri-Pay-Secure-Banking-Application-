import logging
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class InvalidInputError(Exception):
    """Custom exception for invalid user input"""

    def __init__(self, message, field=None, code=400):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class BusinessRuleError(Exception):
    """Custom exception for business rule violations"""

    def __init__(self, message, code=409):
        self.message = message
        self.code = code
        super().__init__(message)


def register_error_handlers(app):
    """Centralized error handler registration"""

    @app.errorhandler(InvalidInputError)
    def handle_invalid_input(error):
        """Handle validation errors"""
        response = {
            'error': error.message,
            'code': 'VALIDATION_ERROR',
            'status': error.code
        }
        if error.field:
            response['field'] = error.field

        logger.warning(f"Validation error: {error.message} - Path: {request.path}")
        return jsonify(response), error.code

    @app.errorhandler(BusinessRuleError)
    def handle_business_error(error):
        """Handle business logic errors"""
        logger.warning(f"Business rule violation: {error.message}")
        return jsonify({
            'error': error.message,
            'code': 'BUSINESS_RULE_ERROR',
            'status': error.code
        }), error.code

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        logger.info(f"404 Not Found: {request.path}")
        return jsonify({
            'error': 'Resource not found',
            'code': 'NOT_FOUND',
            'status': 404,
            'path': request.path
        }), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        """Handle 500 Internal Server errors"""
        logger.error(f"500 Error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'status': 500,
            'request_id': request.environ.get('REQUEST_ID', '')
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catch-all for unhandled exceptions"""
        logger.critical(f"Unhandled exception: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred',
            'code': 'UNKNOWN_ERROR',
            'status': 500
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle Werkzeug HTTP exceptions"""
        response = {
            'error': error.description,
            'code': error.name.upper().replace(' ', '_'),
            'status': error.code
        }
        logger.warning(f"HTTP {error.code}: {error.description}")
        return jsonify(response), error.code
