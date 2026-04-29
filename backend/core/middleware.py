from time import perf_counter

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from common import ApplicationException
from core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (perf_counter() - start_time) * 1000
            response.headers['X-Process-Time'] = f'{elapsed_ms:.2f}ms'
            return response
        except ApplicationException as exc:
            logger.warning('Application exception: %s', exc)
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_dict(),
            )
        except Exception as exc:
            logger.exception('Unhandled exception: %s', exc)
            return JSONResponse(
                status_code=500,
                content={
                    'detail': 'Internal Server Error',
                    'path': str(request.url.path),
                },
            )
