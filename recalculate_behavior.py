from app import app, db
from models import User
from app import update_learning_behavior

with app.app_context():
    print("Recalculating learning behavior for all users...")
    
    users = User.query.all()
    for user in users:
        print(f"Updating user {user.id}: {user.username}")
        try:
            update_learning_behavior(user.id)
            print(f"  ✅ Updated successfully")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ Recalculated behavior for {len(users)} users!")
