"""
Setup script for VKYC project
"""
import os
import subprocess
import sys

def setup_database():
    """Create MySQL database"""
    print("Please create MySQL database manually:")
    print("CREATE DATABASE vkyc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("\nOr run: mysql -u root -p -e 'CREATE DATABASE vkyc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'")

def install_requirements():
    """Install Python requirements"""
    print("Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        print("\n⚠️  Some packages failed to install.")
        print("This is usually due to missing build tools (like Visual C++ on Windows).")
        print("\nTo install Visual C++ Build Tools on Windows:")
        print("1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("2. Install 'Desktop development with C++' workload")
        print("3. Run this setup script again")
        print("\nAlternatively, you can install packages individually:")
        print("  pip install fastapi uvicorn sqlalchemy pymysql")
        print("\nContinuing with partial installation...")
        
        # Try installing core packages without optional ones
        core_packages = [
            "fastapi==0.104.1",
            "uvicorn[standard]==0.24.0",
            "python-multipart==0.0.6",
            "sqlalchemy==2.0.23",
            "pymysql==1.1.0",
            "cryptography==41.0.7",
            "python-jose[cryptography]==3.3.0",
            "passlib[bcrypt]==1.7.4",
            "python-dotenv==1.0.0",
            "aiofiles==23.2.1",
            "opencv-python==4.8.1.78",
            "Pillow==10.1.0",
            "requests==2.31.0",
            "pydantic==2.5.0",
            "pydantic-settings==2.1.0",
            "Django==4.2.7",
            "django-cors-headers==4.3.1",
            "python-dateutil==2.8.2",
            "pytz==2023.3"
        ]
        
        print("\nInstalling core packages...")
        for package in core_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                print(f"  ⚠️  Failed to install {package}")
        
        print("\nNote: mysqlclient and aiortc require build tools and may need manual installation.")

def setup_env():
    """Setup environment files"""
    backend_env = "backend/.env"
    if not os.path.exists(backend_env):
        print("Creating backend/.env from env_example.txt...")
        with open("backend/env_example.txt", "r") as f:
            content = f.read()
        with open(backend_env, "w") as f:
            f.write(content)
        print("Please edit backend/.env with your configuration!")
    else:
        print("backend/.env already exists")

if __name__ == "__main__":
    print("VKYC Project Setup")
    print("=" * 50)
    
    install_requirements()
    setup_env()
    setup_database()
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Edit backend/.env with your API keys and database credentials")
    print("2. Create MySQL database: vkyc_db")
    print("3. Run backend: cd backend && python main.py")
    print("4. Run frontend: cd frontend && python manage.py runserver")

