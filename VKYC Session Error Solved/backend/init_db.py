from database import engine, Base
from models import Customer, VKYCSession, VKYCLog, Agent
import sys

def init_database():
    """Initialize database tables"""
    print("Creating database tables...")
    try:
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        print("   - customers")
        print("   - agents")
        print("   - vkyc_sessions")
        print("   - vkyc_logs")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    response = input("⚠️  This will DELETE all existing data. Continue? (yes/no): ")
    if response.lower() == 'yes':
        init_database()
    else:
        print("Cancelled.")
        sys.exit(0)

