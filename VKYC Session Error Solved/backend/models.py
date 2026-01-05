from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime

class KYCType(str, enum.Enum):
    VKYC = "VKYC"
    EKYC = "EKYC"

class AgentRole(str, enum.Enum):
    AGENT = "Agent"
    QA = "QA"
    LEAD = "Lead"
    ADMIN = "Admin"

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(100), unique=True, index=True)
    name = Column(String(255))
    mobile = Column(String(20))
    email = Column(String(255))
    vkyc_link = Column(Text)
    kyc_type = Column(Enum(KYCType), default=KYCType.VKYC)
    created_on = Column(DateTime, default=datetime.now)
    
    sessions = relationship("VKYCSession", back_populates="customer")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    mobile = Column(String(20))
    role = Column(Enum(AgentRole), default=AgentRole.AGENT)
    is_active = Column(String(10), default="active")  # active, inactive
    restrict_vkyc = Column(String(10), default="no")  # yes, no
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    sessions = relationship("VKYCSession", back_populates="agent")

class VKYCSession(Base):
    __tablename__ = "vkyc_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    unique_id = Column(String(100), index=True)
    status = Column(String(50), default="pending")  # pending, scheduled, started, waiting_for_agent, agent_joined, in_progress, completed, failed, disconnected
    scheduled_time = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    agent_assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    video_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    customer = relationship("Customer", back_populates="sessions")
    agent = relationship("Agent", back_populates="sessions")
    logs = relationship("VKYCLog", back_populates="session")

class VKYCLog(Base):
    __tablename__ = "vkyc_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("vkyc_sessions.id"))
    log_type = Column(String(50))  # pan_detection, aadhaar_detection, digilocker_verification, biometric, location, ip_address
    log_data = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("VKYCSession", back_populates="logs")

