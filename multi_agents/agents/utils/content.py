def text_content(value) -> str:
    """Extract text from a string, AIMessage, or provider text blocks."""
    if hasattr(value, "content"):
        value = value.content
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    raise TypeError(f"Expected text or text blocks; received {type(value).__name__}")
