# VKYC Installation Guide

## Windows Installation

### Prerequisites

1. **Python 3.10+** - Download from [python.org](https://www.python.org/downloads/)

2. **MySQL Database** - Download from [mysql.com](https://dev.mysql.com/downloads/mysql/)

3. **Visual C++ Build Tools** (Optional, for advanced features)
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++" workload
   - Required only if you need `aiortc` or `mysqlclient` packages

### Step 1: Create MySQL Database

```sql
CREATE DATABASE vkyc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 2: Install Python Packages

#### Option A: Using setup.py (Recommended)

```bash
python setup.py
```

This will attempt to install all packages. If some fail (like `aiortc` or `mysqlclient`), it will continue with core packages.

#### Option B: Manual Installation

Install core packages first:

```bash
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install python-multipart==0.0.6
pip install sqlalchemy==2.0.23
pip install pymysql==1.1.0
pip install cryptography==41.0.7
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install python-dotenv==1.0.0
pip install aiofiles==23.2.1
pip install opencv-python==4.8.1.78
pip install Pillow==10.1.0
pip install requests==2.31.0
pip install pydantic==2.5.0
pip install pydantic-settings==2.1.0
pip install Django==4.2.7
pip install django-cors-headers==4.3.1
pip install python-dateutil==2.8.2
pip install pytz==2023.3
```

For `mysqlclient` (requires Visual C++ Build Tools):
```bash
pip install mysqlclient==2.2.0
```

For `aiortc` (optional, requires Visual C++ Build Tools):
```bash
pip install aiortc==1.6.0
```

**Note:** If you get errors installing `mysqlclient`, you can use `pymysql` instead (already installed above). Just make sure your database connection string uses `pymysql` driver.

### Step 3: Configure Environment

1. Copy `backend/env_example.txt` to `backend/.env`

2. Edit `backend/.env` with your configuration:

```env
# Database (use pymysql if mysqlclient failed to install)
DATABASE_URL=mysql+pymysql://root:your_password@localhost/vkyc_db?charset=utf8mb4

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

### Step 4: Run Backend

```bash
cd backend
python main.py
```

Backend will run on `http://localhost:8000`

### Step 5: Run Frontend

Open a new terminal:

```bash
cd frontend
python manage.py runserver
```

Frontend will run on `http://localhost:8000` (or 8001 if 8000 is taken)

### Step 6: Create Django Superuser (Optional)

```bash
cd frontend
python manage.py createsuperuser
```

## Troubleshooting

### Error: Microsoft Visual C++ 14.0 or greater is required

**Solution:** Install Visual C++ Build Tools from https://visualstudio.microsoft.com/visual-cpp-build-tools/

Or use alternative packages:
- Use `pymysql` instead of `mysqlclient` (already in requirements)
- Skip `aiortc` if you don't need advanced WebRTC features

### Error: Cannot connect to MySQL

**Solution:** 
1. Make sure MySQL is running
2. Check database credentials in `backend/.env`
3. Ensure database `vkyc_db` exists

### Error: Module not found

**Solution:** Make sure you're in the correct virtual environment and all packages are installed:

```bash
pip install -r requirements.txt
```

### OpenCV Installation Issues

If `opencv-python` fails, try:
```bash
pip install opencv-python-headless
```

## Quick Start (Minimal Setup)

If you just want to test the application without all features:

1. Install core packages only (skip `aiortc` and `mysqlclient`)
2. Use SQLite instead of MySQL (modify `backend/database.py`)
3. Skip SMS/Email configuration (they'll fail gracefully)

## Production Deployment

For production:
1. Use proper database (MySQL/PostgreSQL)
2. Set up proper SMTP server
3. Configure all API keys
4. Use environment variables for secrets
5. Set up proper SSL certificates
6. Use a production WSGI server (gunicorn, uvicorn workers)

