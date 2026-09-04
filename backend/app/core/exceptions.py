from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging import logger

class PayPilotException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundException(PayPilotException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with id '{resource_id}' was not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=404
        )

class PolicyViolationException(PayPilotException):
    def __init__(self, rule_name: str, reason: str):
        super().__init__(
            message=f"Policy rule '{rule_name}' violated: {reason}",
            code="POLICY_VIOLATION",
            status_code=422
        )

class SignatureVerificationException(PayPilotException):
    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(
            message=message,
            code="INVALID_SIGNATURE",
            status_code=401
        )

class PaymentGatewayException(PayPilotException):
    def __init__(self, message: str = "Payment Gateway interaction failed"):
        super().__init__(
            message=message,
            code="PAYMENT_GATEWAY_ERROR",
            status_code=502
        )

class ValidationException(PayPilotException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400
        )

async def paypilot_exception_handler(request: Request, exc: PayPilotException):
    logger.error(f"PayPilotException [{exc.code}] path={request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "path": request.url.path
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error path={request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.errors(),
                "path": request.url.path
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"An unexpected error occurred on the server: {str(exc)}",
                "path": request.url.path
            }
        }
    )

