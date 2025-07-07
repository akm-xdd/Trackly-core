#!/usr/bin/env python3
"""
Database initialization script for Docker container
- Runs Alembic migrations
- Verifies all required tables exist
- Creates test users if they don't exist
"""

import os
import sys
import time
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
from alembic.config import Config
from alembic import command

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.databases.postgres import SessionLocal, Base
from app.schemas.user_schema import UserSchema
from app.schemas.issue_schema import IssueSchema
from app.schemas.file_schema import FileSchema
from app.schemas.daily_stats_schema import DailyStatsSchema
from app.models.user import UserRole
from app.utils.auth import hash_password


def wait_for_db(database_url: str, max_retries: int = 30):
    """Wait for database to be ready"""
    engine = create_engine(database_url)
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
        except OperationalError as e:
            print(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
            time.sleep(2)
    
    print("❌ Database connection failed after all retries")
    return False


def run_migrations():
    """Run Alembic migrations"""
    try:
        print("🔄 Running Alembic migrations...")
        
        # Create alembic configuration
        alembic_cfg = Config("/app/alembic.ini")
        alembic_cfg.set_main_option("script_location", "/app/alembic")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False


def verify_tables():
    """Verify all required tables exist"""
    try:
        print("🔍 Verifying required tables...")
        
        # Required tables
        required_tables = ['users', 'issues', 'files', 'daily_stats']
        
        engine = create_engine(os.getenv("DATABASE_URL"))
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        missing_tables = []
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✅ Table '{table}' exists")
            else:
                print(f"  ❌ Table '{table}' missing")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            print("🔧 Attempting to create tables using SQLAlchemy...")
            
            # Fallback: Create tables using SQLAlchemy
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created using SQLAlchemy fallback")
        
        return True
        
    except Exception as e:
        print(f"❌ Table verification failed: {str(e)}")
        return False


def create_test_users():
    """Create test users if they don't exist"""
    try:
        print("👥 Creating test users...")
        
        db = SessionLocal()
        
        # Test users to create
        test_users = [
            {
                "email": "admin@trackly.com",
                "password": "admin123",
                "full_name": "Admin User",
                "role": UserRole.ADMIN
            },
            {
                "email": "maintainer@trackly.com", 
                "password": "maintainer123",
                "full_name": "Maintainer User",
                "role": UserRole.MAINTAINER
            },
            {
                "email": "reporter@trackly.com",
                "password": "reporter123", 
                "full_name": "Reporter User",
                "role": UserRole.REPORTER
            },
            {
                "email": "ctfu.anand@gmail.com",
                "password": "google123",
                "full_name": "Anand (Google)",
                "role": UserRole.ADMIN
            }
        ]
        
        created_count = 0
        
        for user_data in test_users:
            # Check if user already exists
            existing_user = db.query(UserSchema).filter(
                UserSchema.email == user_data["email"]
            ).first()
            
            if not existing_user:
                # Create new user
                hashed_password = hash_password(user_data["password"])
                
                new_user = UserSchema(
                    email=user_data["email"],
                    password=hashed_password,
                    full_name=user_data["full_name"],
                    role=user_data["role"]
                )
                
                db.add(new_user)
                created_count += 1
                print(f"  ✅ Created user: {user_data['email']} ({user_data['role'].value})")
            else:
                print(f"  ⏭️  User already exists: {user_data['email']}")
        
        db.commit()
        db.close()
        
        print(f"✅ Test users setup completed. Created {created_count} new users.")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test users: {str(e)}")
        return False


def create_sample_data():
    """Create some sample issues and stats for testing"""
    try:
        print("📊 Creating sample data...")
        
        db = SessionLocal()
        
        # Check if we already have issues
        existing_issues = db.query(IssueSchema).count()
        if existing_issues > 0:
            print("  ⏭️  Sample data already exists")
            db.close()
            return True
        
        # Get users for creating sample issues
        admin_user = db.query(UserSchema).filter(UserSchema.role == UserRole.ADMIN).first()
        reporter_user = db.query(UserSchema).filter(UserSchema.role == UserRole.REPORTER).first()
        
        if admin_user and reporter_user:
            from app.models.issue import IssueSeverity, IssueStatus
            
            # Create sample issues
            sample_issues = [
                {
                    "title": "Login page not responsive on mobile",
                    "description": "The login form doesn't scale properly on mobile devices",
                    "severity": IssueSeverity.HIGH,
                    "status": IssueStatus.OPEN,
                    "created_by": reporter_user.id
                },
                {
                    "title": "Dashboard loading slowly",
                    "description": "Dashboard takes more than 5 seconds to load",
                    "severity": IssueSeverity.MEDIUM,
                    "status": IssueStatus.TRIAGED,
                    "created_by": admin_user.id
                },
                {
                    "title": "Export feature request",
                    "description": "Need ability to export issues to CSV",
                    "severity": IssueSeverity.LOW,
                    "status": IssueStatus.IN_PROGRESS,
                    "created_by": reporter_user.id
                }
            ]
            
            for issue_data in sample_issues:
                new_issue = IssueSchema(**issue_data)
                db.add(new_issue)
            
            db.commit()
            print("  ✅ Created sample issues")
        
        db.close()
        print("✅ Sample data creation completed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create sample data: {str(e)}")
        return False


def main():
    """Main initialization function"""
    print("🚀 Starting database initialization...")
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Wait for database to be ready
    if not wait_for_db(database_url):
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Verify all tables exist
    if not verify_tables():
        sys.exit(1)
    
    # Create test users
    if not create_test_users():
        sys.exit(1)
    
    # Create sample data
    if not create_sample_data():
        print("⚠️  Sample data creation failed, but continuing...")
    
    print("🎉 Database initialization completed successfully!")
    print("\n📋 Test Users Created:")
    print("  👑 admin@trackly.com / admin123 (ADMIN)")
    print("  🔧 maintainer@trackly.com / maintainer123 (MAINTAINER)")
    print("  📝 reporter@trackly.com / reporter123 (REPORTER)")
    print("  🌐 ctfu.anand@gmail.com / google123 (ADMIN - for Google OAuth)")


if __name__ == "__main__":
    main()