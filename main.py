import asyncio
import os
import json
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import our custom agent
from src.agent import BrowserAgent

# Load environment variables
load_dotenv()

# --- 1. Define Your Output Schema ---
# This tells the Agent exactly what data structure you want back.
class Product(BaseModel):
    name: str = Field(description="Name of the product")
    price: str = Field(description="Price of the product")
    url: str = Field(description="Link to the product page")

class ScrapeResult(BaseModel):
    products: list[Product]
    total_found: int

# --- 2. Main Execution ---
async def main():
    # Check for Azure keys (since you switched to Azure)
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ Error: AZURE_OPENAI_API_KEY not found in .env file")
        return

    # Initialize Browser Session
    # Initialize Browser Session
    from src.browser import BrowserSession, BrowserProfile

    # Initialize Browser Session with persistence
    # Use a persistent user_data_dir to save cookies and session data
    user_data_dir = os.path.join(os.getcwd(), "browser_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    profile = BrowserProfile(
        headless=True,  # Set to True for headless mode (FASTER)
        browser_type="chromium", # Options: "chromium", "firefox", "webkit"
        user_data_dir=user_data_dir,
        block_resources=False
    )
    session = BrowserSession(profile)
    
    try:
        await session.start()

        # Define the Task
        target_url = "https://webscraper.io/test-sites/e-commerce/allinone"
        task = f"""
    Navigate to {target_url}.
    Scrape the first 3 products.
    Return the data in the specified JSON format.
    
    Hint: The price is likely in the product container, not the link itself. 
    Use `get_element(index, level=2)` to get the full product card text.
    """
        print(f"🚀 Starting Custom BrowserAgent (Azure OpenAI)...")
        print(f"🎯 Task: {task}\n")

        # Initialize Agent
        agent = BrowserAgent(session, ScrapeResult, use_vision=True)
        
        # Run Agent
        result = await agent.run(task)

        # Output Result
        print("\n" + "="*50)
        print("🏁 FINAL RESULT")
        print("="*50)
        
        # Handle cases where result might be None or error
        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("No result returned.")
        
        # Keep browser open for a moment to inspect
        await asyncio.sleep(5)
    finally:
        await session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Execution stopped by user.")
