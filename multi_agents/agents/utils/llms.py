"""Optional minimal model factory. Preserve your existing factory if compatible."""
def create_model(model_name: str):
    if not isinstance(model_name, str) or "/" not in model_name:
        raise ValueError("Set a model as provider/model_id, via task fields or RESEARCH_ASSISTANT_MODEL")
    provider, model_id = model_name.split("/", 1)
    if not model_id:
        raise ValueError("model_id cannot be empty")
    if provider == "google_genai":
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model=model_id, api_key=key, temperature=0, max_retries=2)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_id, temperature=0, max_retries=2)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_id, temperature=0, max_retries=2)
    raise ValueError(f"Unsupported provider: {provider}")
