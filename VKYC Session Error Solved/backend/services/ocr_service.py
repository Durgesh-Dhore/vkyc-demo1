import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

PAN_OCR_API = os.getenv("PAN_OCR_API", "http://localhost:8001/api/ocr/pan")
AADHAAR_OCR_API = os.getenv("AADHAAR_OCR_API", "http://localhost:8001/api/ocr/aadhaar")

async def extract_pan_info(image_base64: str):
    """Extract PAN information using OCR API"""
    try:
        response = requests.post(
            PAN_OCR_API,
            json={"image": image_base64},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        return {"success": False, "error": "OCR API error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def extract_aadhaar_info(image_base64: str):
    """Extract Aadhaar information using OCR API"""
    try:
        response = requests.post(
            AADHAAR_OCR_API,
            json={"image": image_base64},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        return {"success": False, "error": "OCR API error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

