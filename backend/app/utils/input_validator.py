"""
Input validation utilities for API endpoints.
Enforces length limits, bounds checking, and role allowlists.
"""

MAX_SIMULATION_REQUIREMENT_LENGTH = 5000
MAX_CHAT_MESSAGE_LENGTH = 2000
MAX_CHAT_HISTORY_LENGTH = 20
ALLOWED_CHAT_ROLES = {'user', 'assistant'}
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 5000
MAX_CHUNK_OVERLAP = 500


def validate_simulation_requirement(text):
    """Validate simulation requirement input. Returns (cleaned_text, error_message)."""
    if not text or not text.strip():
        return None, "Simulation requirement is required"
    text = text.strip()
    if len(text) > MAX_SIMULATION_REQUIREMENT_LENGTH:
        return None, f"Simulation requirement too long (max {MAX_SIMULATION_REQUIREMENT_LENGTH} characters)"
    return text, None


def validate_chat_message(text):
    """Validate chat message input. Returns (cleaned_text, error_message)."""
    if not text or not text.strip():
        return None, "Please provide a message"
    text = text.strip()
    if len(text) > MAX_CHAT_MESSAGE_LENGTH:
        return None, f"Message too long (max {MAX_CHAT_MESSAGE_LENGTH} characters)"
    return text, None


def validate_chat_history(history):
    """Validate and sanitize chat history. Returns (cleaned_history, error_message)."""
    if not isinstance(history, list):
        return [], None
    if len(history) > MAX_CHAT_HISTORY_LENGTH:
        history = history[-MAX_CHAT_HISTORY_LENGTH:]
    cleaned = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get('role', '')
        content = entry.get('content', '')
        if role not in ALLOWED_CHAT_ROLES:
            continue
        cleaned.append({'role': role, 'content': str(content)})
    return cleaned, None


def validate_chunk_params(chunk_size, chunk_overlap):
    """Validate chunk size and overlap parameters. Returns (size, overlap, error_message)."""
    try:
        chunk_size = int(chunk_size)
    except (TypeError, ValueError):
        return None, None, "chunk_size must be an integer"
    try:
        chunk_overlap = int(chunk_overlap)
    except (TypeError, ValueError):
        return None, None, "chunk_overlap must be an integer"

    if chunk_size < MIN_CHUNK_SIZE or chunk_size > MAX_CHUNK_SIZE:
        return None, None, f"chunk_size must be between {MIN_CHUNK_SIZE} and {MAX_CHUNK_SIZE}"
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        return None, None, "chunk_overlap must be >= 0 and less than chunk_size"

    return chunk_size, chunk_overlap, None
