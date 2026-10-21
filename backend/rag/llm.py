from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings

@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    """Create the chat model on first use (not at import time) and reuse it afterwards."""
    if not settings.GOOGLE_API_KEY:
        # TODO
        print("GOOGLE_API_KEY is empty. Add it to .env (https://aistudio.google.com/apikey).")
    return ChatGoogleGenerativeAI(
        model=settings.llm_model_name,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.llm_temperature,
    )