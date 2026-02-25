from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.i18n import t, get_locale_from_header


def localized_error_response(
    request: Request,
    error_key: str,
    status_code: int = 400,
    **kwargs
) -> JSONResponse:
    """
    Create a localized error response.
    
    Args:
        request: FastAPI request object
        error_key: Translation key for error message
        status_code: HTTP status code
        **kwargs: Additional format parameters
    
    Returns:
        JSONResponse with localized error message
    """
    locale = get_locale_from_header(request.headers.get("Accept-Language"))
    message = t(error_key, locale, **kwargs)
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": message}
    )


def localized_success_response(
    request: Request,
    success_key: str,
    data: dict | None = None,
    **kwargs
) -> JSONResponse:
    """
    Create a localized success response.
    
    Args:
        request: FastAPI request object
        success_key: Translation key for success message
        data: Additional response data
        **kwargs: Additional format parameters
    
    Returns:
        JSONResponse with localized success message
    """
    locale = get_locale_from_header(request.headers.get("Accept-Language"))
    message = t(success_key, locale, **kwargs)
    
    response_data = {"message": message}
    if data:
        response_data.update(data)
    
    return JSONResponse(content=response_data)
