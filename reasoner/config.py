# reasoner/config.py
import os

AZURE_OPENAI_BASE = os.getenv("AZURE_OPENAI_BASE", "https://your-openai-endpoint.openai.azure.com/")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT", "gpt-4o-mini")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-06-01")
