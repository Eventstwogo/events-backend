import os
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from routes import api_router
from shared.core.config import settings
from shared.core.request_context import request_context
from lifespan import lifespan
from shared.utils.execution_time import ExecutionTimeMiddleware


def create_app() -> FastAPI:

    fastapi_app: FastAPI = FastAPI(
        title=settings.APP_NAME,
        openapi_url="/events.json",
        version="0.1.0",
        description="Events Service API",
        lifespan=lifespan,
        debug=settings.ENVIRONMENT == "development",
    )

    @fastapi_app.get(path="/", tags=["System"])
    async def root() -> dict[str, str]:
        return {
            "message": "Welcome to Events2go API Services",
            "version": "1.0.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        }

    @fastapi_app.get(path="/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "message": "API is running fine!"}

    @fastapi_app.get("/favicon.ico", tags=["System"])
    async def favicon():
        return RedirectResponse(url="/media/favicon.ico")

    fastapi_app.include_router(router=api_router)

    return fastapi_app


app: FastAPI = create_app()

origins = settings.cors_origins
print("CORS Origins: ", origins)

app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        method: str = request.method
        path: str = request.url.path
        request_context.set(request)  # store current request globally
        response: Response = await call_next(request)

        # You can log or add headers here if needed
        response.headers["X-Method"] = method
        response.headers["X-Path"] = path
        return response


# Mount media directory
os.makedirs(name=settings.MEDIA_ROOT, exist_ok=True)
app.mount(
    path="/media", app=StaticFiles(directory=settings.MEDIA_ROOT), name="media"
)

app.add_middleware(
    middleware_class=GZipMiddleware, minimum_size=1000
)  # Adjust as needed
app.add_middleware(ExecutionTimeMiddleware)

# Adding middleware to the app
app.add_middleware(middleware_class=RequestLoggingMiddleware)


@app.exception_handler(HTTPException)
async def handle_http_exceptions(
    request: Request, exc: HTTPException
) -> JSONResponse:
    # Use `request` minimally just to satisfy linters
    path = request.url.path  # Access path to avoid unused warning
    return JSONResponse(
        status_code=exc.status_code,
        content=(
            exc.detail
            if isinstance(exc.detail, dict)
            else {"message": str(exc.detail), "path": path}
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        reload_delay=15,
    )
