# How to Run VKYC Project

## Quick Start

You need to run **TWO servers** - one for the backend (FastAPI) and one for the frontend (Django).

### Terminal 1 - Start FastAPI Backend

```bash
cd backend
python main.py
```

Backend will run on: **http://localhost:8001**

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Terminal 2 - Start Django Frontend

```bash
cd frontend
python manage.py runserver
```

Frontend will run on: **http://localhost:8000**

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

## Access the Application

1. **Admin Dashboard**: http://localhost:8000
2. **Customer Profiles**: http://localhost:8000/customer-profiles/
3. **Backend API Docs**: http://localhost:8001/docs

## Important Notes

- **Backend must be running** before using the frontend, otherwise you'll see connection errors
- Backend runs on port **8001**
- Frontend runs on port **8000**
- Make sure MySQL database is running and configured in `backend/.env`

## Troubleshooting

### Error: "Cannot connect to backend"

**Solution**: Make sure the FastAPI backend is running on port 8001. Check Terminal 1.

### Error: "Module not found"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Error: Database connection failed

**Solution**: 
1. Make sure MySQL is running
2. Check `backend/.env` has correct database credentials
3. Create database: `CREATE DATABASE vkyc_db;`

### Port already in use

If port 8000 or 8001 is already in use:

**For Django (port 8000):**
```bash
python manage.py runserver 8002
```

**For FastAPI (port 8001):**
Edit `backend/main.py` and change:
```python
uvicorn.run(app, host="0.0.0.0", port=8002)  # Change port
```

Then update `frontend/vkyc_admin/settings.py`:
```python
BACKEND_API_URL = 'http://localhost:8002'  # Match the new port
```

## Testing the Setup

1. Open http://localhost:8000/customer-profiles/
2. Click the "+" button (bottom right)
3. Fill in customer details and click "Create"
4. If backend is running, customer will be created
5. If backend is not running, you'll see an error message

## Next Steps

1. Configure API keys in `backend/.env`:
   - MSG91 API key for SMS
   - SMTP settings for email
   - OCR API endpoints
   - DigiLocker API credentials

2. Create a superuser for Django admin:
   ```bash
   cd frontend
   python manage.py createsuperuser
   ```

3. Access Django admin: http://localhost:8000/admin/

