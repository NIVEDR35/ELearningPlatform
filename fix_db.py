from app import app, db
from models import TestResult
from sqlalchemy import text

with app.app_context():
    print("Fixing database schema...")
    
    # Drop the table if it exists
    try:
        db.session.execute(text("DROP TABLE IF EXISTS test_results"))
        db.session.commit()
        print("Dropped test_results table")
    except Exception as e:
        print(f"Error dropping table: {e}")
        
    # Recreate tables
    db.create_all()
    print("Recreated tables")
    
    print("Done!")
