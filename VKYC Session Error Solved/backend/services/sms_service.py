import requests
import os
from dotenv import load_dotenv

load_dotenv()

MSG91_API_KEY = os.getenv("MSG91_API_KEY", "")
MSG91_SENDER_ID = os.getenv("MSG91_SENDER_ID", "VKYC")

async def send_sms(mobile: str, message: str):
    """Send SMS using MSG91 API"""
    try:
        url = "https://control.msg91.com/api/v5/flow/"
        
        # MSG91 Flow API (recommended) or use simple SMS API
        # For simple SMS:
        url = f"https://control.msg91.com/api/sendhttp.php"
        
        params = {
            "authkey": MSG91_API_KEY,
            "mobiles": mobile,
            "message": message,
            "sender": MSG91_SENDER_ID,
            "route": "4",  # Transactional route
            "country": "91"  # India
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

