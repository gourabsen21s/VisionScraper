import asyncio
import logging
import os
import base64
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
    def __init__(self, session: BrowserSession, schema: Type[BaseModel], use_vision: bool = True):
        self.session = session
        self.schema = schema
        self.use_vision = use_vision
        
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
        
        RULES & STRATEGIES:
        1. **DOM Indices**: The [i_xxx] indices are VALID ONLY FOR THE CURRENT STEP. They change after ANY action (click, scroll, navigate).
        2. **Data Extraction**: 
           - Use `get_element(index)` to inspect an element.
           - If the text you need (e.g., price) is not in the element, try `get_element(index, level=1)` or `level=2` to get the parent container's text.
           - **Verify before extracting**: Check if the element exists and has the expected attributes.
        3. **Variable Persistence**: 
           - Variables you define (e.g. `products = []`) PERSIST between steps. You can build up data over multiple steps.
        4. **Visual Context**: 
           - Use the provided screenshot (if available) to understand the page layout.
           - If a popup or cookie banner is blocking the view, close it first.
        5. **Robustness**:
           - If an action fails, try a different approach (e.g., if click fails, try evaluating JS).
           - If the page is empty, try scrolling or waiting (using `await asyncio.sleep(2)`).
        6. **Efficiency**:
           - Try to batch your actions. You can write multiple lines of Python code in one step.
           - Avoid unnecessary navigation.
        """
        
        self.history.append(SystemMessage(content=system_prompt))
        
        step = 1
        while step <= max_steps:
            logger.info(f"--- STEP {step}/{max_steps} ---")
            
            # A. PERCEIVE: Get the DOM state via CDP
            try:
                # Get serialized state from session
                browser_state = await self.session.get_state(include_screenshot=self.use_vision)
                dom_text = DOMTreeSerializer.tree_to_string(browser_state.dom_state._root)
                logger.info(f"DOM Text Length: {len(dom_text)}")
                logger.info(f"DOM Text Preview: {dom_text[:500]}")
            except Exception as e:
                logger.error(f"Error getting state: {e}", exc_info=True)
                dom_text = f"Error reading DOM: {e}"
                browser_state = None

            current_url = self.session.page.url
            
            # B. UPDATE: Construct the user message
            msg_content = []
            
            text_content = f"""
            CURRENT URL: {current_url}
            
            INTERACTIVE DOM STATE:
            {dom_text}
            
            Write the next Python code block to proceed.
            """
            msg_content.append({"type": "text", "text": text_content})
            
            if self.use_vision and browser_state and browser_state.screenshot:
                # browser_state.screenshot is base64 encoded string
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{browser_state.screenshot}"}
                })
            
            self.history.append(HumanMessage(content=msg_content))
            
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
                wrapper_code = f"async def {wrapper_name}():\n{indented_code}\n    return locals()"
                
                # Execute the definition (compiles the function into the namespace)
                exec(wrapper_code, self.namespace)
                
                # Execute the function itself
                local_vars = await self.namespace[wrapper_name]()
                
                # Update namespace with new variables (excluding internal ones)
                if local_vars:
                    self.namespace.update({k: v for k, v in local_vars.items() if not k.startswith('_')})
                
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