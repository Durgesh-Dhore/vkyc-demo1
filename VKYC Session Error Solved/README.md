# VKYC (Video KYC) End-to-End Project

A complete Video KYC system built with FastAPI backend and Django frontend/admin panel.

## Features

- **Customer Management**: Create customers and generate VKYC links
- **SMS/Email Integration**: Send VKYC links via MSG91 SMS and Email
- **VKYC Options**: Start immediately or schedule for later
- **Video Call**: WebRTC-based video communication
- **Document Verification**: PAN and Aadhaar OCR extraction
- **DigiLocker Integration**: Verify documents using DigiLocker API
- **Biometric Logging**: Track blink detection, head movements, IP, location
- **Video Recording**: 10-minute limit with compression
- **Admin Dashboard**: Monitor all VKYC sessions and customer data

## Project Structure

```
.
├── backend/                 # FastAPI backend
│   ├── main.py             # Main FastAPI application
│   ├── database.py         # Database configuration
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── utils.py            # Utility functions
│   ├── services/           # Service modules
│   │   ├── sms_service.py
│   │   ├── email_service.py
│   │   ├── ocr_service.py
│   │   ├── digilocker_service.py
│   │   └── video_service.py
│   └── .env.example
├── frontend/               # Django frontend
│   ├── manage.py
│   ├── vkyc_admin/        # Django project settings
│   ├── dashboard/         # Dashboard app
│   └── templates/         # HTML templates
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Database Setup

Create MySQL database:
```sql
CREATE DATABASE vkyc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration:
# - Database credentials
# - MSG91 API key
# - Email SMTP settings
# - OCR API endpoints
# - DigiLocker API credentials

# Run backend
python main.py
```

Backend will run on `http://localhost:8000`

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Create virtual environment (if not already created)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Run migrations (if needed)
python manage.py migrate

# Create superuser for admin
python manage.py createsuperuser

# Run frontend
python manage.py runserver
```

Frontend will run on `http://localhost:8000` (or port 8001 if 8000 is taken)

## API Endpoints

### Backend (FastAPI)

- `GET /` - API root
- `POST /api/customers/create` - Create customer
- `POST /api/customers/{customer_id}/send-link` - Send VKYC link
- `GET /api/vkyc/{unique_id}` - Get VKYC options
- `POST /api/vkyc/start` - Start VKYC session
- `POST /api/vkyc/schedule` - Schedule VKYC
- `WS /ws/vkyc/{session_id}` - WebSocket for video call
- `GET /api/vkyc/sessions/{session_id}` - Get session details
- `GET /api/customers` - Get all customers

### Frontend (Django)

- `/` - Dashboard home
- `/customer-profiles/` - Customer profiles page
- `/agents/` - Agents management
- `/live-monitoring/` - Live monitoring dashboard
- `/admin/` - Django admin panel

## Environment Variables

Create `.env` file in `backend/` directory:

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost/vkyc_db?charset=utf8mb4

# MSG91 SMS API
MSG91_API_KEY=your_msg91_api_key
MSG91_SENDER_ID=VKYC

# Email SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# OCR APIs
PAN_OCR_API=http://localhost:8001/api/ocr/pan
AADHAAR_OCR_API=http://localhost:8001/api/ocr/aadhaar

# DigiLocker API
DIGILOCKER_API=http://localhost:8002/api/digilocker/verify
DIGILOCKER_API_KEY=your_digilocker_api_key
```

## Usage

1. **Create Customer**: Use Django admin or dashboard to create a customer
2. **Generate Link**: VKYC link is automatically generated
3. **Send Link**: Click "Resend SMS" button to send link via SMS and Email
4. **VKYC Flow**: 
   - User clicks link
   - Chooses "Start Now" or "Schedule"
   - If scheduled, receives new link via SMS/Email
   - If starting now, requests permissions (mic, video, location)
   - Agent asks to show PAN and Aadhaar
   - OCR extracts information
   - DigiLocker verification
   - KYC completion

## Notes

- Video recording is limited to 10 minutes
- All sessions are logged with IP, location, biometrics
- Videos are compressed and saved to `backend/recordings/`
- WebRTC implementation is basic - enhance for production
- OCR and DigiLocker APIs need to be configured with your endpoints

## License

MIT

