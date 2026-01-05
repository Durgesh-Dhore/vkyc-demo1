from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional
import re

class CustomerCreate(BaseModel):
    name: str
    mobile: str
    email: EmailStr
    
    @validator('mobile')
    def validate_mobile(cls, v):
        # Remove spaces and special characters
        mobile = re.sub(r'[^\d]', '', v)
        # Check if it's a valid Indian mobile number (10 digits)
        if len(mobile) == 10 and mobile.isdigit():
            return mobile
        elif len(mobile) == 12 and mobile.startswith('91'):
            return mobile[2:]  # Remove country code
        raise ValueError('Invalid mobile number. Must be 10 digits.')

class CustomerResponse(BaseModel):
    id: int
    unique_id: str
    name: str
    mobile: str
    email: str
    vkyc_link: Optional[str] = None
    created_on: datetime
    
    class Config:
        from_attributes = True

class VKYCStart(BaseModel):
    unique_id: str

class ScheduleVKYC(BaseModel):
    unique_id: str
    scheduled_time: str  # ISO format datetime string

class AgentCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    mobile: str
    role: str = "Agent"  # Agent, QA, Lead, Admin
    
    @validator('mobile')
    def validate_mobile(cls, v):
        mobile = re.sub(r'[^\d]', '', v)
        if len(mobile) == 10 and mobile.isdigit():
            return mobile
        elif len(mobile) == 12 and mobile.startswith('91'):
            return mobile[2:]
        raise ValueError('Invalid mobile number. Must be 10 digits.')
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ["Agent", "QA", "Lead", "Admin"]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v

class AgentResponse(BaseModel):
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    mobile: str
    role: str
    is_active: str
    restrict_vkyc: str
    created_at: datetime
    
    class Config:
        from_attributes = True

