"""
Database initialization script
Creates all tables and optionally seeds sample data
"""

from app import app, db
from models import User, Course, Module, Lesson, UserInteraction, LearningBehavior, LearningStyle, UserConsent, CourseRecommendation
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def init_database():
    """Initialize database tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")

def seed_sample_data():
    """Seed database with sample data for testing"""
    with app.app_context():
        print("\nSeeding sample data...")
        
        # Create sample users
        users = [
            User(
                username='alice',
                email='alice@example.com',
                password_hash=generate_password_hash('password123'),
                role='STUDENT'
            ),
            User(
                username='bob',
                email='bob@example.com',
                password_hash=generate_password_hash('password123'),
                role='STUDENT'
            ),
            User(
                username='charlie',
                email='charlie@example.com',
                password_hash=generate_password_hash('password123'),
                role='STUDENT'
            )
        ]
        
        for user in users:
            db.session.add(user)
        db.session.commit()
        print(f"✅ Created {len(users)} sample users")
        
        # Create sample courses (AI-generated style)
        courses = [
            Course(
                title="Python Programming Fundamentals",
                description="Learn Python from scratch with hands-on exercises and projects. Perfect for visual and kinesthetic learners.",
                difficulty="BEGINNER",
                duration_hours=40,
                tags="python,programming,beginner,coding"
            ),
            Course(
                title="Data Science with Python",
                description="Master data analysis, visualization, and machine learning. Includes video lectures and interactive notebooks.",
                difficulty="INTERMEDIATE",
                duration_hours=60,
                tags="python,data-science,ml,analytics"
            ),
            Course(
                title="Web Development Bootcamp",
                description="Build modern web applications with HTML, CSS, JavaScript, and React. Project-based learning.",
                difficulty="BEGINNER",
                duration_hours=80,
                tags="web,javascript,react,html,css"
            ),
            Course(
                title="Machine Learning A-Z",
                description="Comprehensive ML course covering algorithms, neural networks, and deep learning. Theory and practice combined.",
                difficulty="ADVANCED",
                duration_hours=100,
                tags="ml,ai,deep-learning,neural-networks"
            ),
            Course(
                title="Database Design and SQL",
                description="Learn database concepts, SQL queries, and optimization. Includes practical exercises and real-world examples.",
                difficulty="INTERMEDIATE",
                duration_hours=35,
                tags="database,sql,backend,data"
            )
        ]
        
        for course in courses:
            db.session.add(course)
        db.session.commit()
        print(f"✅ Created {len(courses)} sample courses")
        
        # Create consent for users
        for user in users:
            consent = UserConsent(
                user_id=user.id,
                analytics_consent=True,
                personalization_consent=True,
                data_sharing_consent=False,
                marketing_consent=False,
                ip_address='127.0.0.1',
                user_agent='Sample Data'
            )
            db.session.add(consent)
        db.session.commit()
        print(f"✅ Created consent records for all users")
        
        # Create sample interactions for Alice (Visual learner)
        alice = users[0]
        interaction_types_visual = [
            ('VIDEO_WATCH', 'VIDEO', 1, 300),
            ('VIDEO_WATCH', 'VIDEO', 2, 450),
            ('DIAGRAM_VIEW', 'DOCUMENT', 1, 120),
            ('VIDEO_WATCH', 'VIDEO', 3, 600),
            ('QUIZ_ATTEMPT', 'QUIZ', 1, 180),
            ('VIDEO_WATCH', 'VIDEO', 1, 400),
            ('DOCUMENT_READ', 'DOCUMENT', 2, 200),
        ] * 5  # Repeat to get enough data points
        
        for i, (itype, rtype, rid, duration) in enumerate(interaction_types_visual):
            interaction = UserInteraction(
                user_id=alice.id,
                session_id=f'session-alice-{i // 7}',
                interaction_type=itype,
                resource_type=rtype,
                resource_id=rid,
                duration=duration,
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(interaction)
        
        # Create sample interactions for Bob (Kinesthetic learner)
        bob = users[1]
        interaction_types_kinesthetic = [
            ('QUIZ_ATTEMPT', 'QUIZ', 1, 240),
            ('CODING_EXERCISE', 'ASSIGNMENT', 1, 900),
            ('QUIZ_ATTEMPT', 'QUIZ', 2, 300),
            ('LAB_EXERCISE', 'ASSIGNMENT', 2, 1200),
            ('QUIZ_ATTEMPT', 'QUIZ', 3, 180),
            ('CODING_EXERCISE', 'ASSIGNMENT', 3, 800),
        ] * 5
        
        for i, (itype, rtype, rid, duration) in enumerate(interaction_types_kinesthetic):
            interaction = UserInteraction(
                user_id=bob.id,
                session_id=f'session-bob-{i // 6}',
                interaction_type=itype,
                resource_type=rtype,
                resource_id=rid,
                duration=duration,
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(interaction)
        
        db.session.commit()
        print(f"✅ Created sample interactions for users")
        
        # Create learning behaviors
        alice_behavior = LearningBehavior(
            user_id=alice.id,
            total_time_spent=sum(d for _, _, _, d in interaction_types_visual) * 5,
            avg_session_duration=300,
            preferred_content_type='VIDEO',
            engagement_score=85.5,
            total_sessions=5,
            courses_completed=1,
            courses_in_progress=2
        )
        
        bob_behavior = LearningBehavior(
            user_id=bob.id,
            total_time_spent=sum(d for _, _, _, d in interaction_types_kinesthetic) * 5,
            avg_session_duration=450,
            preferred_content_type='INTERACTIVE',
            engagement_score=92.0,
            total_sessions=5,
            courses_completed=2,
            courses_in_progress=1
        )
        
        db.session.add(alice_behavior)
        db.session.add(bob_behavior)
        db.session.commit()
        print(f"✅ Created learning behavior records")
        
        # Create learning styles
        alice_style = LearningStyle(
            user_id=alice.id,
            visual_score=85,
            auditory_score=45,
            kinesthetic_score=50,
            reading_writing_score=55,
            dominant_style='VISUAL',
            confidence=78.5,
            data_points=35
        )
        
        bob_style = LearningStyle(
            user_id=bob.id,
            visual_score=40,
            auditory_score=35,
            kinesthetic_score=90,
            reading_writing_score=45,
            dominant_style='KINESTHETIC',
            confidence=82.0,
            data_points=30
        )
        
        db.session.add(alice_style)
        db.session.add(bob_style)
        db.session.commit()
        print(f"✅ Created learning style records")
        
        print("\n🎉 Sample data seeded successfully!")
        print("\nSample Users:")
        print("  - alice@example.com (password: password123) - Visual learner")
        print("  - bob@example.com (password: password123) - Kinesthetic learner")
        print("  - charlie@example.com (password: password123) - New user")

if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("  Adaptive Learning System - Database Initialization")
    print("=" * 60)
    
    init_database()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--seed':
        seed_sample_data()
    else:
        print("\nTo seed sample data, run:")
        print("  python init_db.py --seed")
    
    print("\n✅ Database initialization complete!")
    print("=" * 60)
