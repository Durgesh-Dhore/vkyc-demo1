# -- coding: utf-8 --

import secrets
import string
import os


def generate_unique_id(length=10):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def generate_vkyc_link(unique_id: str, session_id: int = None):
    """
    Generate VKYC link using frontend base URL from environment
    """
    base_url = os.getenv("FRONTEND_BASE_URL")

    if not base_url:
        raise ValueError("FRONTEND_BASE_URL is not set in .env")

    if session_id:
        return f"{base_url}/vkyc/{unique_id}?session_id={session_id}"

    return f"{base_url}/vkyc/{unique_id}"