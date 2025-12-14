# api/main.py
import sys
import asyncio

# Fix for Windows: Use SelectorEventLoop instead of ProactorEventLoop
# This is required for Playwright subprocess creation to work
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .deps import init_services
from .routes import session_routes, artifact_routes
from .routes import perception_routes
from .routes import plan_execute, plan_execute_loop
from .routes import screencast_routes

app = FastAPI(title="Browser Runner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Azure Container Apps frontend (will be updated after deployment)
        "https://*.azurecontainerapps.io",
        # Add your custom domain here after configuration
        # "https://yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_services(app)

# include routers
# app.include_router(health_routes.router, prefix="/api")
app.include_router(session_routes.router, prefix="/api")
app.include_router(artifact_routes.router, prefix="/api")
app.include_router(perception_routes.router, prefix="/api")
app.include_router(plan_execute.router, prefix="/api")
app.include_router(plan_execute_loop.router, prefix="/api")
app.include_router(screencast_routes.router, prefix="/api")

