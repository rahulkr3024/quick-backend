#!/usr/bin/env python3
"""
Database initialization script for Quicky AI Summarizer
"""

from app import app, db
from flask import Flask

def init_database():
    """Initialize the database with tables"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Print table information
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📊 Created {len(tables)} tables:")
            for table in tables:
                columns = inspector.get_columns(table)
                print(f"  • {table} ({len(columns)} columns)")
                for col in columns[:3]:  # Show first 3 columns
                    print(f"    - {col['name']} ({col['type']})")
                if len(columns) > 3:
                    print(f"    ... and {len(columns) - 3} more columns")
                print()
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return False
    
    return True

def reset_database():
    """Reset the database (drop and recreate all tables)"""
    with app.app_context():
        try:
            print("⚠️  Dropping all existing tables...")
            db.drop_all()
            print("✅ All tables dropped")
            
            print("🔄 Creating new tables...")
            db.create_all()
            print("✅ Database reset successfully!")
            
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            return False
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("🚨 RESETTING DATABASE - This will delete all data!")
        confirm = input("Are you sure? (type 'yes' to confirm): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("❌ Database reset cancelled")
    else:
        print("🚀 Initializing Quicky database...")
        if init_database():
            print("\n🎉 Database initialization complete!")
            print("\n📝 Next steps:")
            print("1. Set up your environment variables (.env file)")
            print("2. Install dependencies: pip install -r requirements.txt")
            print("3. Run the application: python app.py")
        else:
            print("\n❌ Database initialization failed!")
