import asyncio
import logging
import os
from typing import Type, Dict, Any, Optional
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from pydantic import BaseModel

from src.sanitizer import CodeSanitizer
from src.browser import BrowserSession
from src.tools import Toolset
from src.dom.serializer.service import DOMTreeSerializer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserAgent:
    """
    The main agent class that orchestrates the browser automation.
    It manages the LLM conversation history, variable persistence, 
    and the execution loop.
    """
    def __init__(self, session: BrowserSession, schema: Type[BaseModel]):
        self.session = session
        self.schema = schema
        
        # Initialize Components
        self.tools = Toolset(session)
        
        # Initialize Azure LLM
        # Ensure the following are in your .env file:
        # AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        self.llm = AzureChatOpenAI(
            azure_deployment=deployment_name,
            api_version=api_version,
            temperature=0
        )
        
        # Conversation History
        self.history: list[BaseMessage] = []
        
        # The Persistent Execution Namespace (Jupyter-like memory)
        # We initialize it with our tools (click, navigate, etc.)
        self.namespace = self.tools.get_globals()

    async def run(self, task: str, max_steps: int = 15) -> Dict[str, Any]:
        """
        Runs the agent loop until the task is done or max_steps reached.
        """
        # 1. Initialize System Prompt
        schema_desc = self.schema.model_json_schema()
        system_prompt = f"""
        You are a generic Python browser automation agent.
        
        USER TASK: {task}
        
        REQUIRED OUTPUT SCHEMA (call done() with this structure):
        {schema_desc}
        
        AVAILABLE FUNCTIONS (Already imported):
        - await navigate("url")
        - await click(index)  <-- CRITICAL: Use the [i_xxx] index from the DOM State.
        - await input_text(index, "text")
        - await scroll(amount=None) <-- Scroll down (None) or by pixels.
        - await switch_tab(tab_id)
        - await send_keys("keys") <-- e.g. "Enter", "Tab"
        - await get_element(index, level=0) <-- Returns dict with keys: 'tag_name', 'text_content', 'attributes', 'children_ids'. Use level=1, 2 etc. to get parent/grandparent text.
        - await evaluate("js_code", variables={{}}) 
        - await done(result_dict)
        
        RULES:
        1. The DOM State provided below shows interactive elements with indices [i_xxx].
        2. Indices [i_xxx] are VALID ONLY FOR THE CURRENT STEP. They change after navigation/action.
        3. Write valid Python code. Variables you define (e.g. `products = []`) persist between steps.
        4. Use `get_element(index)` to scrape data. If the text (e.g. price) is visually next to the link but not returned, try `get_element(index, level=2)` to get the container's text.
        5. DO NOT hallucinate element IDs. Only use what you see in the DOM State.
        """
        
        self.history.append(SystemMessage(content=system_prompt))
        
        step = 1
        while step <= max_steps:
            logger.info(f"--- STEP {step}/{max_steps} ---")
            
            # A. PERCEIVE: Get the DOM state via CDP
            try:
                # Get serialized state from session
                browser_state = await self.session.get_state()
                dom_text = DOMTreeSerializer.tree_to_string(browser_state.dom_state._root)
                logger.info(f"DOM Text Length: {len(dom_text)}")
                logger.info(f"DOM Text Preview: {dom_text[:500]}")
            except Exception as e:
                dom_text = f"Error reading DOM: {e}"

            current_url = self.session.page.url
            
            # B. UPDATE: Construct the user message
            user_msg = f"""
            CURRENT URL: {current_url}
            
            INTERACTIVE DOM STATE:
            {dom_text}
            
            Write the next Python code block to proceed.
            """
            self.history.append(HumanMessage(content=user_msg))
            
            # C. THINK: Ask LLM
            logger.info("🤖 Thinking...")
            try:
                response = await self.llm.ainvoke(self.history)
                self.history.append(response)
            except Exception as e:
                logger.error(f"LLM Call failed: {e}")
                return {"error": "LLM failed"}

            # D. ACT: Execute Python
            try:
                # 1. Sanitize
                raw_code = response.content
                code_str = CodeSanitizer.sanitize(raw_code)
                
                logger.info(f"🐍 Executing Code:\n{code_str}")
                
                # 2. Wrap in Async Execution Wrapper
                # This allows the LLM to write 'await click(5)' at the top level
                # and lets us maintain variable persistence.
                
                # Indent code for the wrapper function
                indented_code = "\n".join(["    " + line for line in code_str.splitlines()])
                
                # We define a temporary async function in the namespace
                wrapper_name = f"_step_{step}_runner"
                wrapper_code = f"async def {wrapper_name}():\n{indented_code}"
                
                # Execute the definition (compiles the function into the namespace)
                exec(wrapper_code, self.namespace)
                
                # Execute the function itself
                await self.namespace[wrapper_name]()
                
                # 3. Check for Completion
                if self.tools.is_done:
                    logger.info("🎉 Task Completed Successfully!")
                    return self.tools.final_result
                    
            except Exception as e:
                error_msg = f"Execution Error: {str(e)}"
                logger.error(error_msg)
                # Feed the error back to the LLM so it can self-correct
                self.history.append(HumanMessage(content=f"The previous code failed with: {error_msg}. Please fix it and try again."))
            
            step += 1
            await asyncio.sleep(1) # Brief pause for stability

        return {"error": "Max steps reached without completion"}