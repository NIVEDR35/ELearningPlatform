from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Adding new columns to lessons table...")
    
    columns_to_add = [
        ("assignment", "TEXT"),
        ("document_url", "VARCHAR(500)"),
        ("code_example", "TEXT"),
        ("interactive_element", "TEXT"),
        ("quiz_questions", "TEXT"),
        ("diagram_url", "VARCHAR(500)")
    ]
    
    for column_name, column_type in columns_to_add:
        try:
            db.session.execute(text(f"ALTER TABLE lessons ADD COLUMN {column_name} {column_type}"))
            db.session.commit()
            print(f"✅ Added column: {column_name}")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print(f"⚠️  Column {column_name} already exists, skipping")
            else:
                print(f"❌ Error adding {column_name}: {e}")
            db.session.rollback()
    
    print("Done!")
