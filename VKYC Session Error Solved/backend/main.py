from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from sqlalchemy.orm import Session
import uvicorn
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Set, Optional
import logging
import time
import requests
from services.s3_service import upload_video_to_s3

from database import SessionLocal, engine, Base
from models import Customer, VKYCSession, VKYCLog, Agent, AgentRole
from schemas import CustomerCreate, VKYCStart, ScheduleVKYC, AgentCreate, AgentResponse
from services.sms_service import send_sms
from services.email_service import send_email
from services.ocr_service import extract_pan_info, extract_aadhaar_info
from services.digilocker_service import verify_with_digilocker
from services.video_service import VideoRecorder
from utils import generate_vkyc_link, generate_unique_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")
WS_BASE_URL = os.getenv("WS_BASE_URL")
METERED_API_KEY = os.getenv("METERED_API_KEY")

app = FastAPI(title="VKYC Backend API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# WebSocket connections manager with improved stability
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, dict] = {}  # User connections: session_id -> {websocket, last_heartbeat}
        self.agent_connections: Dict[str, dict] = {}  # Agent connections: agent_id -> {websocket, last_heartbeat}
        self.agent_sessions: Dict[str, int] = {}  # Agent's current session: agent_id -> session_id
        self.session_agents: Dict[int, str] = {}  # Session's agent: session_id -> agent_id
        self.waiting_sessions: Set[int] = set()  # Sessions waiting for agent
        self.recordings: Dict[str, VideoRecorder] = {}
        self.lock = asyncio.Lock()
        
    async def connect_user(self, websocket: WebSocket, session_id: str):
        """Connect a user with proper handshake and state management"""
        await websocket.accept()
        async with self.lock:
            self.active_connections[session_id] = {
                "websocket": websocket,
                "last_heartbeat": datetime.now(),
                "connected_at": datetime.now()
            }
            # Initialize video recorder
            self.recordings[session_id] = VideoRecorder(session_id)
            logger.info(f"User connected for session {session_id}")

    async def connect_agent(self, websocket: WebSocket, employee_id: str):
        """Connect an agent with proper handshake and state management"""
        await websocket.accept()
        async with self.lock:
            self.agent_connections[employee_id] = {
                "websocket": websocket,
                "last_heartbeat": datetime.now(),
                "connected_at": datetime.now()
            }
            logger.info(f"Agent {employee_id} connected")

    async def disconnect_user(self, session_id: str):
        """Safely disconnect a user and clean up resources"""
        async with self.lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                logger.info(f"User disconnected from session {session_id}")
            
            if session_id in self.recordings:
                recorder = self.recordings[session_id]
                try:
                    recorder.stop_recording()
                except Exception as e:
                    logger.error(f"Error stopping recording for session {session_id}: {e}")
                del self.recordings[session_id]
            
            session_id_int = int(session_id) if session_id.isdigit() else None
            # if session_id_int and session_id_int in self.waiting_sessions:
            #     self.waiting_sessions.remove(session_id_int)
            
            if session_id_int and session_id_int in self.session_agents:
                agent_id = self.session_agents[session_id_int]
                if agent_id in self.agent_sessions:
                    del self.agent_sessions[agent_id]
                del self.session_agents[session_id_int]

    async def disconnect_agent(self, employee_id: str):
        """Safely disconnect an agent and clean up resources"""
        async with self.lock:
            if employee_id in self.agent_connections:
                del self.agent_connections[employee_id]
                logger.info(f"Agent {employee_id} disconnected")
            
            if employee_id in self.agent_sessions:
                session_id = self.agent_sessions[employee_id]
                if session_id in self.session_agents:
                    del self.session_agents[session_id]
                del self.agent_sessions[employee_id]

    async def send_to_user(self, message: dict, session_id: str) -> bool:
        """Safely send message to user, return success status"""
        if session_id not in self.active_connections:
            logger.warning(f"Cannot send to user {session_id}: not connected")
            return False
        
        connection = self.active_connections[session_id]
        websocket = connection["websocket"]
        
        try:
            await websocket.send_json(message)
            connection["last_heartbeat"] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error sending to user {session_id}: {e}")
            await self.disconnect_user(session_id)
            return False

    async def send_to_agent(self, message: dict, agent_id: str) -> bool:
        """Safely send message to agent, return success status"""
        if agent_id not in self.agent_connections:
            logger.warning(f"Cannot send to agent {agent_id}: not connected")
            return False
        
        connection = self.agent_connections[agent_id]
        websocket = connection["websocket"]
        
        try:
            await websocket.send_json(message)
            connection["last_heartbeat"] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error sending to agent {agent_id}: {e}")
            await self.disconnect_agent(agent_id)
            return False

    async def broadcast_to_all_agents(self, message: dict):
        """Broadcast message to all connected agents with error handling"""
        disconnected_agents = []
        
        async with self.lock:
            for agent_id, connection in self.agent_connections.items():
                websocket = connection["websocket"]
                try:
                    await websocket.send_json(message)
                    connection["last_heartbeat"] = datetime.now()
                except Exception as e:
                    logger.error(f"Error broadcasting to agent {agent_id}: {e}")
                    disconnected_agents.append(agent_id)
            
            # Clean up disconnected agents
            for agent_id in disconnected_agents:
                await self.disconnect_agent(agent_id)

    def add_waiting_session(self, session_id: int):
        """Add session to waiting list"""
        if session_id in self.waiting_sessions:
            return False
        self.waiting_sessions.add(session_id)
        return True

    async def assign_agent_to_session(self, agent_id: str, session_id: int) -> bool:
        """Assign agent to session with proper locking"""
        async with self.lock:
            # Check if agent already assigned to another session
            if agent_id in self.agent_sessions:
                logger.warning(f"Agent {agent_id} already assigned to session {self.agent_sessions[agent_id]}")
                return False
            
            # Check if session already has an agent
            if session_id in self.session_agents:
                logger.warning(f"Session {session_id} already has agent {self.session_agents[session_id]}")
                return False
            
            self.agent_sessions[agent_id] = session_id
            self.session_agents[session_id] = agent_id
            
            if session_id in self.waiting_sessions:
                self.waiting_sessions.remove(session_id)
            
            logger.info(f"Assigned agent {agent_id} to session {session_id}")
            return True

    def get_available_agent(self) -> Optional[str]:
        """Get first available agent (not assigned to any session)"""
        for agent_id in self.agent_connections:
            if agent_id not in self.agent_sessions:
                return agent_id
        return None

    async def cleanup_stale_connections(self, timeout_seconds: int = 60):
        """Clean up stale connections that haven't sent heartbeats"""
        now = datetime.now()
        stale_users = []
        stale_agents = []
        
        async with self.lock:
            # Check user connections
            for session_id, connection in self.active_connections.items():
                if (now - connection["last_heartbeat"]).total_seconds() > timeout_seconds:
                    stale_users.append(session_id)
            
            # Check agent connections
            for agent_id, connection in self.agent_connections.items():
                if (now - connection["last_heartbeat"]).total_seconds() > timeout_seconds:
                    stale_agents.append(agent_id)
        
        # Clean up stale connections
        for session_id in stale_users:
            logger.info(f"Cleaning up stale user connection for session {session_id}")
            await self.disconnect_user(session_id)
        
        for agent_id in stale_agents:
            logger.info(f"Cleaning up stale agent connection for agent {agent_id}")
            await self.disconnect_agent(agent_id)

manager = ConnectionManager()

# Background task for cleaning up stale connections
async def cleanup_task():
    """Background task to clean up stale connections"""
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds
        try:
            await manager.cleanup_stale_connections()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

# Start cleanup task on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_task())
    logger.info("Cleanup task started")

# Session expiry timer with improved error handling
async def session_expiry_timer(session_id: int, duration_seconds: int):
    """Auto-expire session after duration with proper cleanup"""
    await asyncio.sleep(duration_seconds)
    
    db = SessionLocal()
    try:
        session = db.query(VKYCSession).filter(VKYCSession.id == session_id).first()
        if session and session.status in ["waiting_for_agent", "in_progress"]:
            # Session expired
            session.status = "expired"
            db.commit()
            
            # Notify user if still connected
            await manager.send_to_user({
                "type": "session_expired",
                "message": "Session expired. Please retry."
            }, str(session_id))
            
            # Notify all agents
            await manager.broadcast_to_all_agents({
                "type": "session_expired",
                "session_id": session_id
            })
            
            # Clean up connection
            await manager.disconnect_user(str(session_id))
            
            logger.info(f"Session {session_id} expired after {duration_seconds} seconds")
    except Exception as e:
        logger.error(f"Error in session expiry timer for session {session_id}: {e}")
    finally:
        db.close()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "VKYC Backend API"}

@app.post("/api/customers/create")
async def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    try:
        db_customer = Customer(
            unique_id=generate_unique_id(),
            name=customer.name,
            mobile=customer.mobile,
            email=customer.email,
            created_on=datetime.now()
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        
        # Generate VKYC link
        vkyc_link = generate_vkyc_link(db_customer.unique_id)
        db_customer.vkyc_link = vkyc_link
        db.commit()
        
        return {
            "success": True,
            "customer_id": db_customer.id,
            "unique_id": db_customer.unique_id,
            "vkyc_link": vkyc_link
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/customers/{customer_id}/send-link")
async def send_vkyc_link(customer_id: int, db: Session = Depends(get_db)):
    """Send VKYC link via SMS and Email"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        # Send SMS
        sms_result = await send_sms(
            mobile=customer.mobile,
            message=f"Your VKYC link: {customer.vkyc_link}"
        )
        
        # Send Email
        email_result = await send_email(
            to_email=customer.email,
            subject="VKYC Link",
            body=f"Your VKYC link: {customer.vkyc_link}"
        )
        
        return {
            "success": True,
            "sms_sent": sms_result,
            "email_sent": email_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vkyc/{unique_id}")
async def get_vkyc_options(unique_id: str, db: Session = Depends(get_db)):
    """Get VKYC options (start now or schedule)"""
    customer = db.query(Customer).filter(Customer.unique_id == unique_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer_id": customer.id,
        "unique_id": customer.unique_id,
        "name": customer.name,
        "options": ["start_now", "schedule"]
    }

@app.post("/api/vkyc/schedule")
async def schedule_vkyc(schedule: ScheduleVKYC, db: Session = Depends(get_db)):
    """Schedule a VKYC session"""
    customer = db.query(Customer).filter(Customer.unique_id == schedule.unique_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        scheduled_time = datetime.fromisoformat(schedule.scheduled_time)
        
        # Create scheduled session
        session = VKYCSession(
            customer_id=customer.id,
            unique_id=schedule.unique_id,
            scheduled_time=scheduled_time,
            status="scheduled"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Generate scheduled link
        scheduled_link = generate_vkyc_link(customer.unique_id, session_id=session.id)
        
        # Send SMS and Email with scheduled link
        await send_sms(
            mobile=customer.mobile,
            message=f"Your scheduled VKYC link: {scheduled_link}. Scheduled for: {scheduled_time}"
        )
        
        await send_email(
            to_email=customer.email,
            subject="Scheduled VKYC Link",
            body=f"Your scheduled VKYC link: {scheduled_link}. Scheduled for: {scheduled_time}"
        )
        
        return {
            "success": True,
            "session_id": session.id,
            "scheduled_link": scheduled_link,
            "scheduled_time": scheduled_time.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/vkyc/start")
async def start_vkyc(vkyc_start: VKYCStart, db: Session = Depends(get_db)):
    print("?? VKYC START PAYLOAD:", vkyc_start.dict())

    customer = db.query(Customer).filter(
        Customer.unique_id == vkyc_start.unique_id
    ).first()

    print("?? CUSTOMER FOUND:", customer)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # ?? CRITICAL DUPLICATE SESSION GUARD
    existing_session = db.query(VKYCSession).filter(
        VKYCSession.customer_id == customer.id,
        VKYCSession.status.in_([
            "started",
            "waiting_for_agent",
            "in_progress",
            "disconnected"
        ])
    ).order_by(VKYCSession.id.desc()).first()

    if existing_session:
        print("?? REUSING EXISTING SESSION:", existing_session.id)
        return {
            "success": True,
            "session_id": existing_session.id,
            "websocket_url": f"{WS_BASE_URL}/ws/vkyc/{existing_session.id}"
        }

    # ? CREATE NEW SESSION ONLY IF NONE EXISTS
    try:
        session = VKYCSession(
            customer_id=customer.id,
            unique_id=vkyc_start.unique_id,
            status="started",
            started_at=datetime.now()
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        print("? NEW SESSION CREATED:", session.id)

        return {
            "success": True,
            "session_id": session.id,
            "websocket_url": f"{WS_BASE_URL}/ws/vkyc/{session.id}"
        }

    except Exception as e:
        print("? REAL ERROR:", repr(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/vkyc/{session_id}")
async def websocket_vkyc(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for VKYC video call (User side) with improved stability"""
    await manager.connect_user(websocket, str(session_id))
    
    db = SessionLocal()
    try:
        session = db.query(VKYCSession).filter(VKYCSession.id == session_id).first()
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return
        
        # ?? CRITICAL FIX: ensure session is visible to agents
        # if session.status in ("started", "disconnected"):
        #     session.status = "waiting_for_agent"
        #     session.started_at = datetime.now()
        #     db.commit()

        #     manager.add_waiting_session(session_id)

        #     customer = db.query(Customer).filter(
        #         Customer.id == session.customer_id
        #     ).first()

        #     await manager.broadcast_to_all_agents({
        #         "type": "new_waiting_session",
        #         "session_id": session_id,
        #         "customer_id": session.customer_id,
        #         "unique_id": session.unique_id,
        #         "customer_name": customer.name if customer else "Unknown",
        #         "customer_mobile": customer.mobile if customer else "",
        #         "started_at": session.started_at.isoformat()
        #     })

        #     logger.info(f"[AUTO-WAITING] Session {session_id} promoted to waiting_for_agent")

        
        # Send heartbeat interval to client
        await manager.send_to_user({
            "type": "heartbeat_interval",
            "interval": 30  # Send heartbeat every 30 seconds
        }, str(session_id))
        
        try:
            while True:
                try:
                    # Receive with timeout to detect stale connections
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=60.0  # 1 minute timeout
                    )
                    
                    message_type = data.get("type")
                    
                    # Handle heartbeat
                    if message_type == "heartbeat":
                        # Just update connection timestamp, no response needed
                        continue

                    elif message_type == "user_left":
                        logger.info(f"[VKYC] User manually left session {session_id}")

                        # ?? Update session status
                        session.status = "disconnected"
                        db.commit()

                        # ?? Notify assigned agent (if any)
                        if session_id in manager.session_agents:
                            agent_id = manager.session_agents[session_id]
                            await manager.send_to_agent({
                                "type": "user_left",
                                "session_id": session_id,
                                "message": "User has left the VKYC session"
                            }, agent_id)

                        # ?? Stop recording safely
                        recorder = manager.recordings.get(str(session_id))
                        if recorder:
                            try:
                                recorder.stop_recording()
                            except Exception as e:
                                logger.error(f"Recording stop failed for {session_id}: {e}")

                        # ?? Cleanup user connection
                        await manager.disconnect_user(str(session_id))
                        break

                    elif message_type == "ready_for_agent":
                        logger.info(f"[READY_FOR_AGENT] received for session {session_id}")

                        session.status = "waiting_for_agent"
                        session.started_at = datetime.now()
                        db.commit()

                        # ? DEDUP GATE
                        added = manager.add_waiting_session(session_id)

                        if added:
                            customer = db.query(Customer).filter(
                                Customer.id == session.customer_id
                            ).first()

                            await manager.broadcast_to_all_agents({
                                "type": "new_waiting_session",
                                "session_id": session_id,
                                "customer_id": session.customer_id,
                                "unique_id": session.unique_id,
                                "customer_name": customer.name if customer else "Unknown",
                                "customer_mobile": customer.mobile if customer else "",
                                "started_at": session.started_at.isoformat()
                            })

                        # Notify user
                        await manager.send_to_user({
                            "type": "waiting_for_agent",
                            "message": "Waiting for an available agent..."
                        }, str(session_id))

                        asyncio.create_task(session_expiry_timer(session_id, 300)) # 5 minutes = 300 seconds
  
                    
                    elif message_type == "permissions_granted":
                        # Legacy support - if permissions granted before ready_for_agent
                        pass
                    
                    elif message_type == "document_captured":
                        # Document captured by user (auto-capture)
                        doc_type = data.get("doc_type")  # "pan", "aadhaar_front", "aadhaar_back", etc.
                        doc_image = data.get("image")

                        # Process OCR based on document type
                        if doc_type == "pan":
                            ocr_result = await extract_pan_info(doc_image)
                            log_type = "pan_detection"
                        elif isinstance(doc_type, str) and doc_type.startswith("aadhaar"):
                            # Accept aadhaar, aadhaar_front, aadhaar_back
                            ocr_result = await extract_aadhaar_info(doc_image)
                            if doc_type == "aadhaar_front":
                                log_type = "aadhaar_front_detection"
                            elif doc_type == "aadhaar_back":
                                log_type = "aadhaar_back_detection"
                            else:
                                log_type = "aadhaar_detection"
                        else:
                            ocr_result = {"error": "Invalid document type"}
                            log_type = "document_capture_error"
                        
                        # Log document capture
                        log = VKYCLog(
                            session_id=session_id,
                            log_type=log_type,
                            log_data=json.dumps(ocr_result)
                        )
                        db.add(log)
                        db.commit()
                        
                        # Check if OCR was successful
                        success = ocr_result.get("success", False) or "error" not in ocr_result
                        
                        # Notify user
                        await manager.send_to_user({
                            "type": "document_verification_result",
                            "doc_type": doc_type,
                            "success": success,
                            "data": ocr_result,
                            "message": f"{doc_type.upper()} Verified" if success else "Verification Failed. Please try again."
                        }, str(session_id))
                        
                        # Notify agent
                        if session_id in manager.session_agents:
                            agent_id = manager.session_agents[session_id]
                            await manager.send_to_agent({
                                "type": "document_verification_result",
                                "session_id": session_id,
                                "doc_type": doc_type,
                                "success": success,
                                "data": ocr_result
                            }, agent_id)

                    elif message_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice_candidate"):
                        # Forward WebRTC signaling messages to the assigned agent
                        if session_id in manager.session_agents:
                            agent_id = manager.session_agents[session_id]
                            payload = data.get('payload') if isinstance(data, dict) else None
                            await manager.send_to_agent({
                                "type": message_type,
                                "session_id": session_id,
                                "payload": payload
                            }, agent_id)
                    
                    elif message_type == "pan_detected":
                        # Legacy support - Extract PAN info using OCR
                        pan_image = data.get("image")
                        pan_info = await extract_pan_info(pan_image)
                        
                        # Log PAN detection
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="pan_detection",
                            log_data=json.dumps(pan_info)
                        )
                        db.add(log)
                        db.commit()
                        
                        await manager.send_to_user({
                            "type": "pan_extracted",
                            "data": pan_info
                        }, str(session_id))
                    
                    elif message_type == "aadhaar_detected":
                        # Legacy support - Extract Aadhaar info using OCR
                        aadhaar_image = data.get("image")
                        aadhaar_info = await extract_aadhaar_info(aadhaar_image)
                        
                        # Log Aadhaar detection
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="aadhaar_detection",
                            log_data=json.dumps(aadhaar_info)
                        )
                        db.add(log)
                        db.commit()
                        
                        await manager.send_to_user({
                            "type": "aadhaar_extracted",
                            "data": aadhaar_info
                        }, str(session_id))
                    
                    elif message_type == "verify_digilocker":
                        # Verify with DigiLocker
                        doc_type = data.get("doc_type")  # "pan" or "aadhaar"
                        doc_info = data.get("doc_info")
                        
                        verification_result = await verify_with_digilocker(doc_type, doc_info)
                        
                        # Log verification
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="digilocker_verification",
                            log_data=json.dumps(verification_result)
                        )
                        db.add(log)
                        db.commit()
                        
                        await manager.send_to_user({
                            "type": "digilocker_result",
                            "success": verification_result.get("success", False),
                            "message": verification_result.get("message", "")
                        }, str(session_id))
                    
                    elif message_type == "biometric_data":
                        # Log biometric data (blink detection, head movements, etc.)
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="biometric",
                            log_data=json.dumps(data.get("data", {}))
                        )
                        db.add(log)
                        db.commit()
                    
                    elif message_type == "location_data":
                        # Log location data
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="location",
                            log_data=json.dumps(data.get("location", {}))
                        )
                        db.add(log)
                        db.commit()
                    
                    elif message_type == "ip_address":
                        # Log IP address
                        log = VKYCLog(
                            session_id=session_id,
                            log_type="ip_address",
                            log_data=json.dumps({"ip": data.get("ip")})
                        )
                        db.add(log)
                        db.commit()
                    
                    elif message_type == "kyc_complete":
                        # Complete KYC
                        session.status = "completed"
                        session.completed_at = datetime.now()
                        
                        # Stop recording
                        recorder = manager.recordings.get(str(session_id))
                        if recorder:
                            video_path = recorder.stop_recording()
                            session.video_path = video_path
                        
                        db.commit()
                        
                        # Notify user
                        await manager.send_to_user({
                            "type": "kyc_completed",
                            "message": "Your KYC is complete!"
                        }, str(session_id))
                        
                        # Notify agent
                        if session_id in manager.session_agents:
                            agent_id = manager.session_agents[session_id]
                            await manager.send_to_agent({
                                "type": "session_completed",
                                "session_id": session_id,
                                "message": "VKYC session completed successfully"
                            }, agent_id)
                        
                        # Broadcast to all agents
                        await manager.broadcast_to_all_agents({
                            "type": "session_completed",
                            "session_id": session_id
                        })
                        
                        # Close connection after completion
                        break
                    
                    elif message_type == "error":
                        session.status = "failed"
                        session.error_message = data.get("message", "Unknown error")
                        db.commit()
                        
                except asyncio.TimeoutError:
                    # Send ping to check if connection is still alive
                    try:
                        await websocket.send_json({"type": "ping"})
                        # Wait for pong
                        response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                        if response.get("type") != "pong":
                            logger.warning(f"No pong response from session {session_id}")
                            break
                    except:
                        logger.warning(f"Session {session_id} connection appears to be dead")
                        break
                    
        except WebSocketDisconnect:
            logger.info(f"User WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket for session {session_id}: {e}")
        finally:
            # Clean up on disconnect
            await manager.disconnect_user(str(session_id))
            if session and session.status == "in_progress":
                session.status = "disconnected"
                db.commit()
            
    except Exception as e:
        logger.error(f"Error setting up WebSocket for session {session_id}: {e}")
    finally:
        db.close()

@app.websocket("/ws/agent/{employee_id}")
async def websocket_agent(websocket: WebSocket, employee_id: str):
    """WebSocket endpoint for Agent connections using EMPLOYEE ID"""

    # 1?? Accept & register agent using employee_id
    await manager.connect_agent(websocket, employee_id)

    db = SessionLocal()
    try:
        # 2?? Validate agent using employee_id (NOT numeric id)
        agent = db.query(Agent).filter(
            Agent.employee_id == employee_id
        ).first()

        if not agent:
            await websocket.close(code=1008, reason="Agent not found")
            return

        logger.info(f"Agent connected with employee_id={employee_id}")

        # 3?? Send heartbeat config
        await manager.send_to_agent({
            "type": "heartbeat_interval",
            "interval": 30
        }, employee_id)

        # 4?? Send waiting sessions list
        waiting_sessions = db.query(VKYCSession).filter(
            VKYCSession.status == "waiting_for_agent"
        ).all()

        sessions_data = []
        for s in waiting_sessions:
            customer = db.query(Customer).filter(
                Customer.id == s.customer_id
            ).first()

            sessions_data.append({
                "session_id": s.id,
                "customer_id": s.customer_id,
                "unique_id": s.unique_id,
                "customer_name": customer.name if customer else "Unknown",
                "customer_mobile": customer.mobile if customer else "",
                "started_at": s.started_at.isoformat() if s.started_at else None
            })

        await manager.send_to_agent({
            "type": "waiting_sessions",
            "sessions": sessions_data
        }, employee_id)

        # 5?? Main receive loop
        try:
            while True:
                try:
                    # Receive with timeout to detect stale connections
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=60.0  # 1 minute timeout
                    )
                    
                    message_type = data.get("type")
                    
                    # Handle heartbeat
                    if message_type == "heartbeat":
                        # Just update connection timestamp, no response needed
                        continue
                    
                    if message_type == "accept_session":
                        session_id = data.get("session_id")
                        session = db.query(VKYCSession).filter(VKYCSession.id == session_id).first()
                        
                        if not session:
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "Session not found"
                            }, employee_id)
                            continue
                        
                        if session.status != "waiting_for_agent":
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "Session is not waiting for agent or already assigned"
                            }, employee_id)
                            continue
                        
                        # Check if agent is already assigned to another session
                        if employee_id in manager.agent_sessions:
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "You are already assigned to another session"
                            }, employee_id)
                            continue
                        
                        # Assign agent to session
                        assigned = await manager.assign_agent_to_session(employee_id, session_id)
                        if not assigned:
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "Could not assign agent to session"
                            }, employee_id)
                            continue
                        manager.waiting_sessions.discard(session_id)
                        
                        session.agent_id = agent.id
                        session.status = "agent_joined"
                        session.agent_assigned_at = datetime.now()
                        db.commit()
                        
                        # Get customer info
                        customer = db.query(Customer).filter(Customer.id == session.customer_id).first()
                        
                        # Notify user
                        await manager.send_to_user({
                            "type": "agent_assigned",
                            "message": "Agent has joined. Starting VKYC session...",
                            "agent_name": f"{agent.first_name} {agent.last_name}"
                        }, str(session_id))
                        
                        # Notify agent
                        await manager.send_to_agent({
                            "type": "session_accepted",
                            "session_id": session_id,
                            "customer_id": session.customer_id,
                            "unique_id": session.unique_id,
                            "customer_name": customer.name if customer else "Unknown",
                            "customer_mobile": customer.mobile if customer else ""
                        }, employee_id)
                        
                        # Broadcast to all other agents that session is taken
                        await manager.broadcast_to_all_agents({
                            "type": "session_taken",
                            "session_id": session_id,
                            "agent_employee_id": employee_id,
                            "agent_name": f"{agent.first_name} {agent.last_name}"
                        })
                        
                        # Start video recording
                        recorder = manager.recordings.get(str(session_id))
                        if recorder:
                            recorder.start_recording()
                        
                        # Update session status to in_progress
                        session.status = "in_progress"
                        db.commit()
                        
                        # Start 5-minute timer for this session
                        asyncio.create_task(session_expiry_timer(session_id, 300))
                    
                    elif message_type == "decline_session":
                        session_id = data.get("session_id")

                        session = db.query(VKYCSession).filter(
                            VKYCSession.id == session_id
                        ).first()

                        if not session:
                            continue

                        # ?? HARD REMOVE from waiting
                        if session_id in manager.waiting_sessions:
                            manager.waiting_sessions.remove(session_id)

                        session.status = "declined"
                        db.commit()

                        # ?? Tell ALL agents to remove it
                        await manager.broadcast_to_all_agents({
                            "type": "session_removed",
                            "session_id": session_id
                        })

                        # ?? Tell user
                        await manager.send_to_user({
                            "type": "agent_declined",
                            "message": "Agent declined. Please retry."
                        }, str(session_id))

                    
                    elif message_type == "request_document_capture":
                        # Agent requests document capture from user
                        session_id = data.get("session_id")
                        doc_type = data.get("doc_type")  # "pan" or "aadhaar"
                        
                        # Verify agent owns this session
                        if employee_id not in manager.agent_sessions or manager.agent_sessions[employee_id] != session_id:
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "You are not assigned to this session"
                            }, employee_id)
                            continue
                        
                        # Forward request to user
                        await manager.send_to_user({
                            "type": "request_document_capture",
                            "doc_type": doc_type,
                            "message": f"Please show your {doc_type.upper()} card"
                        }, str(session_id))
                        
                        # Notify agent that request was sent
                        await manager.send_to_agent({
                            "type": "document_capture_requested",
                            "session_id": session_id,
                            "doc_type": doc_type
                        }, employee_id)

                    elif message_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice_candidate"):
                        # Forward WebRTC signaling messages to the user side
                        session_id = data.get('session_id')
                        payload = data.get('payload') if isinstance(data, dict) else None
                        if session_id and str(session_id) in manager.active_connections:
                            await manager.send_to_user({
                                "type": message_type,
                                "session_id": session_id,
                                "payload": payload
                            }, str(session_id))
                    
                    elif message_type == "cancel_document_capture":
                        # Agent cancels document capture
                        session_id = data.get("session_id")
                        
                        # Verify agent owns this session
                        if employee_id not in manager.agent_sessions or manager.agent_sessions[employee_id] != session_id:
                            await manager.send_to_agent({
                                "type": "error",
                                "message": "You are not assigned to this session"
                            }, employee_id)
                            continue
                        
                        # Forward cancel to user
                        await manager.send_to_user({
                            "type": "cancel_document_capture",
                            "message": "Document capture cancelled"
                        }, str(session_id))
                    
                    elif message_type == "leave_session":
                        session_id = data.get("session_id")
                        if employee_id in manager.agent_sessions and manager.agent_sessions[employee_id] == session_id:
                            session = db.query(VKYCSession).filter(VKYCSession.id == session_id).first()
                            if session:
                                session.status = "waiting_for_agent"
                                session.agent_id = None
                                db.commit()
                                
                                # Remove agent assignment
                                if session_id in manager.session_agents:
                                    del manager.session_agents[session_id]
                                if employee_id in manager.agent_sessions:
                                    del manager.agent_sessions[employee_id]
                                
                                manager.add_waiting_session(session_id)
                                
                                await manager.send_to_user({
                                    "type": "agent_left",
                                    "message": "Agent has left. Waiting for new agent..."
                                }, str(session_id))
                                
                                await manager.send_to_agent({
                                    "type": "session_left",
                                    "session_id": session_id,
                                    "message": "You left the session"
                                }, employee_id)
                                
                                # Broadcast to all agents that session is available again
                                await manager.broadcast_to_all_agents({
                                    "type": "session_available",
                                    "session_id": session_id
                                })
                    
                except asyncio.TimeoutError:
                    # Send ping to check if connection is still alive
                    try:
                        await websocket.send_json({"type": "ping"})
                        # Wait for pong
                        response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                        if response.get("type") != "pong":
                            logger.warning(f"No pong response from agent {employee_id}")
                            break
                    except:
                        logger.warning(f"Agent {employee_id} connection appears to be dead")
                        break
                    
        except WebSocketDisconnect:
            logger.info(f"Agent WebSocket disconnected for agent {employee_id}")
        except Exception as e:
            logger.error(f"Error in Agent WebSocket for agent {employee_id}: {e}")
        finally:
            session_id = manager.agent_sessions.get(employee_id)

            if session_id:
                recorder = manager.recordings.get(str(session_id))
                if recorder:
                    try:
                        recorder.stop_recording()
                        logger.info(
                            f"Recording stopped due to agent disconnect (session {session_id})"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to stop recording on agent disconnect: {e}"
                        )

            await manager.disconnect_agent(employee_id)
                    
    except Exception as e:
        logger.error(f"Error setting up Agent WebSocket for agent {employee_id}: {e}")
    finally:
        db.close()

@app.get("/api/vkyc/sessions/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get VKYC session details"""
    session = db.query(VKYCSession).filter(VKYCSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logs = db.query(VKYCLog).filter(VKYCLog.session_id == session_id).all()
    
    return {
        "session": {
            "id": session.id,
            "customer_id": session.customer_id,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "video_path": session.video_path
        },
        "logs": [{"type": log.log_type, "data": json.loads(log.log_data)} for log in logs]
    }

@app.get("/api/customers")
async def get_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all customers"""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers

# Agent Management APIs
@app.post("/api/agents/create", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent"""
    try:
        # Check if employee_id already exists
        existing = db.query(Agent).filter(Agent.employee_id == agent.employee_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")
        
        # Check if email already exists
        existing_email = db.query(Agent).filter(Agent.email == agent.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Map role string to enum
        role_map = {
            "Agent": AgentRole.AGENT,
            "QA": AgentRole.QA,
            "Lead": AgentRole.LEAD,
            "Admin": AgentRole.ADMIN
        }
        
        db_agent = Agent(
            employee_id=agent.employee_id,
            first_name=agent.first_name,
            last_name=agent.last_name,
            email=agent.email,
            mobile=agent.mobile,
            role=role_map.get(agent.role, AgentRole.AGENT),
            is_active="active",
            restrict_vkyc="no"
        )
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        
        return db_agent
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/agents", response_model=list[AgentResponse])
async def get_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all agents"""
    agents = db.query(Agent).offset(skip).limit(limit).all()
    return agents

@app.get("/api/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """Get agent by ID"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.get("/api/agents/available")
async def get_available_agents(db: Session = Depends(get_db)):
    """Get list of available agents (active and not restricted)"""
    agents = db.query(Agent).filter(
        Agent.is_active == "active",
        Agent.restrict_vkyc == "no"
    ).all()
    return [{"id": a.id, "employee_id": a.employee_id, "name": f"{a.first_name} {a.last_name}"} for a in agents]

@app.get("/api/sessions/waiting")
async def get_waiting_sessions(db: Session = Depends(get_db)):
    """Get all sessions waiting for agent"""
    sessions = db.query(VKYCSession).filter(
        VKYCSession.status == "waiting_for_agent"
    ).all()
    return [{
        "session_id": s.id,
        "customer_id": s.customer_id,
        "unique_id": s.unique_id,
        "started_at": s.started_at.isoformat() if s.started_at else None
    } for s in sessions]

@app.get("/vkyc/{unique_id}", response_class=HTMLResponse)
async def vkyc_page(unique_id: str):
    """Serve VKYC page"""
    vkyc_html_path = Path(__file__).parent.parent / "frontend" / "templates" / "vkyc" / "vkyc_page.html"
    if vkyc_html_path.exists():
        return FileResponse(vkyc_html_path)
    else:
        # Fallback HTML
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>VKYC</title></head>
        <body>
            <h1>VKYC Page for {unique_id}</h1>
            <p>VKYC page template not found. Please ensure the template file exists.</p>
        </body>
        </html>
        """)



@app.get("/api/turn-credentials")
async def get_turn_credentials():
    """
    Fetch TURN/STUN credentials from Metered and format for WebRTC
    This API is consumed by frontend before creating RTCPeerConnection
    """
    # Default STUN servers as fallback
    default_ice_servers = [
        { "urls": "stun:stun.l.google.com:19302" },
        { "urls": "stun:stun1.l.google.com:19302" },
    ]

    if not METERED_API_KEY:
        logger.warning("TURN API key not configured, using STUN only")
        return default_ice_servers

    url = f"https://regtechapi.metered.live/api/v1/turn/credentials?apiKey={METERED_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Convert Metered response to WebRTC format
        ice_servers = []
        
        # Add TURN servers from Metered response
        if isinstance(data, list):
            for server in data:
                if "urls" in server:
                    ice_servers.append(server)
        elif isinstance(data, dict):
            if "urls" in data:
                ice_servers.append(data)
            elif "iceServers" in data:
                ice_servers.extend(data["iceServers"])
        
        # Add default STUN servers for better connectivity
        ice_servers.extend(default_ice_servers)
        
        logger.info(f"Returning {len(ice_servers)} ICE servers")
        return ice_servers

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch TURN credentials: {e}")
        logger.info("Falling back to STUN servers only")
        return default_ice_servers




VIDEO_DIR = "videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    file_bytes = await file.read()

    s3_path = upload_video_to_s3(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type
    )

    return {
        "success": True,
        "message": "Video uploaded to S3",
        "s3_path": s3_path
    }

# VIDEO_DIR = "videos"
# os.makedirs(VIDEO_DIR, exist_ok=True)

# @app.post("/api/upload-video")
# async def upload_video(file: UploadFile = File(...)):
#     """Save uploaded video file locally"""
#     file_path = os.path.join(VIDEO_DIR, file.filename)

#     with open(file_path, "wb") as f:
#         f.write(await file.read())

#     return {
#         "success": True,
#         "message": "Video saved successfully",
#         "file_path": file_path
#     }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ws_ping_interval=20,  # Send ping every 20 seconds
        ws_ping_timeout=60,   # Close if no pong for 60 seconds
        timeout_keep_alive=30,
        log_level="info"
    )