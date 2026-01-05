import requests
import os
from dotenv import load_dotenv

load_dotenv()

DIGILOCKER_API = os.getenv("DIGILOCKER_API", "http://localhost:8002/api/digilocker/verify")
DIGILOCKER_API_KEY = os.getenv("DIGILOCKER_API_KEY", "")

async def verify_with_digilocker(doc_type: str, doc_info: dict):
    """Verify document with DigiLocker API"""
    try:
        response = requests.post(
            DIGILOCKER_API,
            json={
                "doc_type": doc_type,  # "pan" or "aadhaar"
                "doc_info": doc_info
            },
            headers={
                "Authorization": f"Bearer {DIGILOCKER_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": result.get("verified", False),
                "message": result.get("message", "Verification completed"),
                "data": result.get("data", {})
            }
        return {
            "success": False,
            "message": "DigiLocker API error"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

