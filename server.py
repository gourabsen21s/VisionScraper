import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.agent import BrowserAgent
from src.browser.session import BrowserSession
from src.browser.profile import BrowserProfile

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class GenericResult(BaseModel):
    data: Dict[str, Any] = Field(description="The result of the task, structured as a dictionary.")

@app.get("/")
async def root():
    return {"status": "ok", "message": "BrowserAgent Server is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    try:
        while True:
            # Receive task
            data = await websocket.receive_json()
            task = data.get("task")
            
            if not task:
                await websocket.send_json({"error": "No task provided"})
                continue
                
            logger.info(f"Received task: {task}")
            
            # Initialize Agent for this task
            # Use a separate user data dir for the server to avoid conflicts if main.py is run
            user_data_dir = os.path.join(os.getcwd(), "browser_data_server")
            
            # Create profile
            profile = BrowserProfile(
                headless=True,
                browser_type="chromium",
                user_data_dir=user_data_dir,
                block_resources=True,
                wait_until="domcontentloaded"
            )
            
            session = BrowserSession(profile)
            
            try:
                await session.start()
                
                # Initialize Agent with GenericResult schema
                agent = BrowserAgent(session=session, schema=GenericResult)
                
                # Run agent
                # We'll use a reasonable max_steps
                result = await agent.run(task, max_steps=20)
                
                # Send result
                await websocket.send_json({"status": "success", "result": result})
                
            except Exception as e:
                logger.error(f"Task failed: {e}", exc_info=True)
                await websocket.send_json({"status": "error", "message": str(e)})
            finally:
                await session.close()
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
