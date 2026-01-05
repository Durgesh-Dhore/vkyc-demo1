# VKYC Quick Start Guide

## Fixing Installation Issues

If you're getting errors installing packages (especially `aiortc` or `mysqlclient`), here's a quick fix:

### Option 1: Skip Problematic Packages (Recommended for Testing)

The application will work without `aiortc` for basic functionality. Just install core packages:

```bash
pip install fastapi uvicorn sqlalchemy pymysql cryptography python-jose passlib python-dotenv aiofiles opencv-python Pillow requests pydantic pydantic-settings Django django-cors-headers python-dateutil pytz
```

### Option 2: Install Visual C++ Build Tools (For Full Features)

1. Download Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++" workload
3. Restart your computer
4. Run `python setup.py` again

### Option 3: Use Pre-built Wheels

For `mysqlclient`, you can try:
```bash
pip install --only-binary :all: mysqlclient
```

## Database Setup

1. Create MySQL database:
```sql
CREATE DATABASE vkyc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Update `backend/.env`:
```env
DATABASE_URL=mysql+pymysql://root:your_password@localhost/vkyc_db?charset=utf8mb4
```

Note: Using `pymysql` instead of `mysqlclient` works fine and doesn't require build tools.

## Running the Application

### Terminal 1 - Backend:
```bash
cd backend
python main.py
```

### Terminal 2 - Frontend:
```bash
cd frontend
python manage.py runserver
```

## Testing

1. Open browser: http://localhost:8000 (or 8001 for Django)
2. Go to Customer Profiles
3. Click the "+" button to create a customer
4. Click "Resend SMS" to send VKYC link

## Common Issues

**Issue:** `ModuleNotFoundError: No module named 'cv2'`
**Fix:** `pip install opencv-python`

**Issue:** `Cannot connect to MySQL`
**Fix:** Check MySQL is running and credentials in `backend/.env`

**Issue:** `aiortc` installation fails
**Fix:** This is optional. The app works without it for basic video features.

## Next Steps

1. Configure MSG91 API key in `backend/.env` for SMS
2. Configure SMTP settings for email
3. Set up your OCR API endpoints
4. Set up DigiLocker API credentials

See `INSTALLATION.md` for detailed instructions.

