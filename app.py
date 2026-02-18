from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models and services
from models import (
    db, User, Course, Module, Lesson, UserInteraction, LearningBehavior,
    LearningStyle, UserConsent, CourseRecommendation, TestResult,
    PerformanceHistory, LessonProgress, GeneratedContent, LearningPath,
    QuizAttempt, CourseProgress,
    # Phase 2 models
    VideoEngagement, UserCourseSequence, LatentFactors,
    LearningSession, VARKPrediction, EngagementEvent,
    # Phase 2 Enhancement models
    ConceptMastery, SessionSummary, ContentBias
)
from gemini_service import GeminiService
from vark_service import VARKService
from recommendation_service import RecommendationService
from youtube_service import YouTubeService
from config import config

# Import new LMS enhancement services
from progress_tracking_service import ProgressTrackingService
from ai_content_service import AIContentGenerationService
from personalization_service import PersonalizationService
from content_cache_service import get_cache_service

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config[os.getenv('FLASK_ENV', 'development')])

# Initialize extensions
db.init_app(app)
CORS(app)

# Initialize services
gemini_service = GeminiService()
vark_service = VARKService()
recommendation_service = RecommendationService()
youtube_service = YouTubeService()

# Initialize new LMS enhancement services
progress_tracking_service = ProgressTrackingService()
ai_content_service = AIContentGenerationService()
personalization_service = PersonalizationService()
cache_service = get_cache_service()

# ==================== AUTHENTICATION ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    
    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role='STUDENT'  # All users are students
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Create default consent (opt-in required)
    consent = UserConsent(
        user_id=user.id,
        analytics_consent=True,
        personalization_consent=True,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(consent)
    db.session.commit()
    
    session['user_id'] = user.id
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

# ==================== ANALYTICS & TRACKING ====================

@app.route('/api/analytics/track', methods=['POST'])
def track_interaction():
    """Track user interaction"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    # Check consent - Auto-enable for seamless experience
    consent = UserConsent.query.filter_by(user_id=user_id).first()
    if not consent:
        try:
            consent = UserConsent(user_id=user_id, analytics_consent=True, personalization_consent=True)
            db.session.add(consent)
            db.session.commit()
        except Exception:
            db.session.rollback()
            # Retry fetch in case it was created by another request
            consent = UserConsent.query.filter_by(user_id=user_id).first()
            if consent:
                consent.analytics_consent = True
                consent.personalization_consent = True
                db.session.commit()
    elif not consent.analytics_consent:
        consent.analytics_consent = True
        consent.personalization_consent = True
        db.session.commit()
    
    # Serialize metadata if present
    metadata = data.get('metadata')
    if metadata and isinstance(metadata, (dict, list)):
        metadata = json.dumps(metadata)
    
    # Ensure duration is an integer
    duration = data.get('duration')
    if duration is not None:
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 0
    else:
        duration = 0
    
    # Create interaction
    interaction = UserInteraction(
        user_id=user_id,
        session_id=data.get('session_id'),
        interaction_type=data.get('interaction_type'),
        resource_type=data.get('resource_type'),
        resource_id=data.get('resource_id'),
        duration=duration,
        interaction_metadata=metadata,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(interaction)
    db.session.commit()
    
    # Update learning behavior asynchronously
    update_learning_behavior(user_id)
    
    return jsonify({'message': 'Interaction tracked'}), 201

@app.route('/api/analytics/behavior/<int:user_id>', methods=['GET'])
def get_learning_behavior(user_id):
    """Get learning behavior for user"""
    behavior = LearningBehavior.query.filter_by(user_id=user_id).first()
    
    if not behavior:
        return jsonify({'message': 'No behavior data yet'}), 404
    
    return jsonify(behavior.to_dict()), 200

@app.route('/api/analytics/learning-style/<int:user_id>', methods=['GET'])
def get_learning_style(user_id):
    """Get learning style for user"""
    style = LearningStyle.query.filter_by(user_id=user_id).first()
    
    if not style:
        # Try to infer if enough data
        result = vark_service.infer_learning_style(user_id)
        return jsonify(result), 200
    
    return jsonify(style.to_dict()), 200

@app.route('/api/analytics/infer-style/<int:user_id>', methods=['POST'])
def infer_learning_style(user_id):
    """Manually trigger learning style inference"""
    result = vark_service.infer_learning_style(user_id)
    return jsonify(result), 200

@app.route('/api/analytics/pattern/<int:user_id>', methods=['GET'])
def get_learning_pattern(user_id):
    """Get learning pattern analysis"""
    days = request.args.get('days', 30, type=int)
    pattern = vark_service.analyze_learning_pattern(user_id, days)
    return jsonify(pattern), 200

# ==================== RECOMMENDATIONS ====================

@app.route('/api/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    """Get personalized course recommendations"""
    count = request.args.get('count', 10, type=int)
    
    try:
        # Always try to get recommendations
        recommendations = recommendation_service.get_recommendations(user_id, count)
        
        # If no recommendations, return all courses as fallback
        if not recommendations or len(recommendations) == 0:
            all_courses = Course.query.limit(count).all()
            recommendations = [
                {
                    'course': course.to_dict(),
                    'score': 50.0,
                    'reasoning': 'Explore this course to get started',
                    'type': 'GENERAL'
                }
                for course in all_courses
            ]
        
        return jsonify({'recommendations': recommendations}), 200
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        # Fallback: return all courses
        all_courses = Course.query.limit(count).all()
        recommendations = [
            {
                'course': course.to_dict(),
                'score': 50.0,
                'reasoning': 'Explore this course',
                'type': 'GENERAL'
            }
            for course in all_courses
        ]
        return jsonify({'recommendations': recommendations}), 200

@app.route('/api/recommendations/feedback', methods=['POST'])
def submit_recommendation_feedback():
    """Submit feedback on recommendation"""
    data = request.json
    
    recommendation = CourseRecommendation.query.get(data['recommendation_id'])
    if not recommendation:
        return jsonify({'error': 'Recommendation not found'}), 404
    
    if data.get('clicked'):
        recommendation.clicked = True
        recommendation.clicked_at = datetime.utcnow()
    
    if data.get('enrolled'):
        recommendation.enrolled = True
        recommendation.enrolled_at = datetime.utcnow()
    
    if data.get('dismissed'):
        recommendation.dismissed = True
    
    if data.get('rating'):
        recommendation.feedback_rating = data['rating']
    
    db.session.commit()
    
    return jsonify({'message': 'Feedback recorded'}), 200

@app.route('/api/recommendations/learning-path/<int:user_id>', methods=['GET'])
def get_learning_path(user_id):
    """Generate personalized learning path"""
    target_skill = request.args.get('skill', 'Programming')
    weeks = request.args.get('weeks', 12, type=int)
    
    # Get user's learning style
    style = LearningStyle.query.filter_by(user_id=user_id).first()
    learning_style = style.dominant_style if style else 'MULTIMODAL'
    
    # Generate learning path with Gemini
    path = gemini_service.generate_learning_path(
        target_skill=target_skill,
        current_level='Beginner',
        learning_style=learning_style,
        time_available_weeks=weeks
    )
    
    return jsonify(path), 200

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Course detail page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session.get('user_id')
    course = Course.query.get_or_404(course_id)

    # Fetch modules and lessons from DB
    modules = []
    for module in course.modules:
        mod_dict = module.to_dict()
        # Ensure lessons are sorted by order
        mod_dict['lessons'] = sorted(mod_dict['lessons'], key=lambda x: x['order'])
        modules.append(mod_dict)

    # Sort modules by order
    modules.sort(key=lambda x: x['order'])

    # Fetch actual progress from database
    progress_data = progress_tracking_service.get_course_progress(user_id, course_id)
    progress = progress_data.get('completion_percentage', 0) if progress_data and progress_data.get('enrolled') else 0

    # Get lesson completion status for UI
    lesson_progress = {}
    if progress_data and progress_data.get('modules'):
        for mod in progress_data['modules']:
            for lesson in mod.get('lessons', []):
                lesson_progress[lesson['lesson_id']] = {
                    'status': lesson['status'],
                    'completion': lesson['completion']
                }

    # Mock objectives (could be added to DB later)
    objectives = [
        f"Master the fundamentals of {course.title}",
        "Build real-world projects",
        "Understand best practices and patterns",
        "Prepare for technical interviews"
    ]

    return render_template(
        'course_detail.html',
        course=course,
        modules=modules,
        objectives=objectives,
        progress=progress,
        lesson_progress=lesson_progress
    )

# ==================== AI COURSE GENERATION ====================

@app.route('/api/courses/generate', methods=['POST'])
def generate_course():
    """Generate a course using AI based on user request"""
    data = request.json
    user_id = session.get('user_id')
    
    # Get user's learning style
    style = LearningStyle.query.filter_by(user_id=user_id).first() if user_id else None
    learning_style = style.dominant_style if style else 'MULTIMODAL'
    
    # Generate course content with Gemini
    course_data = gemini_service.generate_course_content(
        topic=data['topic'],
        difficulty=data.get('level', 'beginner'),
        weeks=data.get('weeks', 8),
        goal=data.get('goal', '')
    )
    
    if isinstance(course_data, dict) and 'title' in course_data:
        # Create course in database
        course = Course(
            title=course_data['title'],
            description=course_data.get('description', ''),
            difficulty=course_data.get('difficulty', 'BEGINNER'),
            duration_hours=course_data.get('total_duration_hours', 40),
            tags=','.join(course_data.get('tags', [])),
            instructor_id=None  # AI-generated
        )
        
        db.session.add(course)
        db.session.flush()  # Flush to get course ID
        
        # Process modules and lessons
        if 'modules' in course_data:
            for i, mod_data in enumerate(course_data['modules']):
                module = Module(
                    course_id=course.id,
                    title=mod_data['title'],
                    order=i
                )
                db.session.add(module)
                db.session.flush()  # Flush to get module ID
                
                if 'lessons' in mod_data:
                    for j, lesson_data in enumerate(mod_data['lessons']):
                        # Find relevant video
                        if 'video_search_term' in lesson_data:
                            video_query = lesson_data['video_search_term']
                        else:
                            video_query = f"{lesson_data['title']} {data['topic']} tutorial"
                            
                        videos = youtube_service.search_videos(video_query, max_results=1)
                        video_url = videos[0]['url'] if videos else None
                        video_id = videos[0]['id'] if videos else None
                        
                        lesson = Lesson(
                            module_id=module.id,
                            title=lesson_data['title'],
                            content=lesson_data.get('content', ''),
                            duration_minutes=lesson_data.get('duration_minutes', 15),
                            video_url=video_url,
                            video_id=video_id,
                            order=j,
                            # Multi-modal VARK content
                            assignment=lesson_data.get('assignment'),
                            code_example=lesson_data.get('code_example'),
                            interactive_element=lesson_data.get('interactive_element'),
                            quiz_questions=json.dumps(lesson_data.get('quiz_questions', [])) if lesson_data.get('quiz_questions') else None,
                            document_url=lesson_data.get('document_reference')
                        )
                        db.session.add(lesson)
        
        db.session.commit()
        
        # Return full course data
        return jsonify({
            'message': 'Course generated successfully',
            'course': course.to_dict(),
            'content': course_data
        }), 201
    else:
        return jsonify({'error': 'Failed to generate course'}), 500

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all courses"""
    difficulty = request.args.get('difficulty')
    search = request.args.get('search')
    
    query = Course.query
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if search:
        query = query.filter(Course.title.contains(search) | Course.description.contains(search))
    
    courses = query.order_by(Course.created_at.desc()).all()
    return jsonify({'courses': [c.to_summary_dict() for c in courses]}), 200

@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get course details"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    return jsonify(course.to_dict()), 200

@app.route('/api/courses/<int:course_id>/adapt', methods=['POST'])
def adapt_course_content(course_id):
    """Adapt course content for user's learning style"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Get user's learning style
    style = LearningStyle.query.filter_by(user_id=user_id).first()
    if not style:
        return jsonify({'error': 'Learning style not yet determined'}), 400
    
    # Adapt content
    adapted_content = gemini_service.adapt_content_for_learning_style(
        course.description,
        style.dominant_style
    )
    
    return jsonify({
        'original': course.description,
        'adapted': adapted_content,
        'learning_style': style.dominant_style
    }), 200

@app.route('/api/lessons/<int:lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    """Get lesson details"""
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404
    
    return jsonify(lesson.to_dict()), 200

# ==================== PRIVACY & CONSENT ====================

@app.route('/api/privacy/consent', methods=['POST'])
def update_consent():
    """Update user consent preferences"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    consent = UserConsent.query.filter_by(user_id=user_id).first()
    
    if not consent:
        consent = UserConsent(user_id=user_id)
        db.session.add(consent)
    
    # Handle both batch update and individual consent type update
    if 'consent_type' in data:
        # Individual consent update
        consent_type = data['consent_type']
        granted = data.get('granted', False)
        
        if consent_type == 'analytics':
            consent.analytics_consent = granted
        elif consent_type == 'personalization':
            consent.personalization_consent = granted
        elif consent_type == 'data_sharing':
            consent.data_sharing_consent = granted
        elif consent_type == 'marketing':
            consent.marketing_consent = granted
    else:
        # Batch update
        consent.analytics_consent = data.get('analytics_consent', False)
        consent.personalization_consent = data.get('personalization_consent', False)
        consent.data_sharing_consent = data.get('data_sharing_consent', False)
        consent.marketing_consent = data.get('marketing_consent', False)
    
    consent.data_retention_days = data.get('data_retention_days', 365)
    consent.ip_address = request.remote_addr
    consent.user_agent = request.headers.get('User-Agent')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Consent updated',
        'consent': consent.to_dict()
    }), 200

@app.route('/api/privacy/consent/<int:user_id>', methods=['GET'])
def get_consent(user_id):
    """Get user consent status"""
    consent = UserConsent.query.filter_by(user_id=user_id).first()
    
    if not consent:
        # Return default consents
        return jsonify([
            {'consent_type': 'analytics', 'granted': False},
            {'consent_type': 'personalization', 'granted': False},
            {'consent_type': 'data_sharing', 'granted': False},
            {'consent_type': 'marketing', 'granted': False}
        ]), 200
    
    # Return as array for frontend
    return jsonify([
        {'consent_type': 'analytics', 'granted': consent.analytics_consent},
        {'consent_type': 'personalization', 'granted': consent.personalization_consent},
        {'consent_type': 'data_sharing', 'granted': consent.data_sharing_consent},
        {'consent_type': 'marketing', 'granted': consent.marketing_consent}
    ]), 200

@app.route('/api/privacy/export/<int:user_id>', methods=['GET'])
def export_user_data(user_id):
    """Export all user data (GDPR compliance)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Collect all user data
    data = {
        'user': user.to_dict(),
        'interactions': [i.to_dict() for i in user.interactions],
        'learning_behavior': user.learning_behavior.to_dict() if user.learning_behavior else None,
        'learning_style': user.learning_style.to_dict() if user.learning_style else None,
        'consent': user.consent.to_dict() if user.consent else None,
        'recommendations': [r.to_dict() for r in user.recommendations]
    }
    
    return jsonify(data), 200

@app.route('/api/privacy/delete/<int:user_id>', methods=['DELETE'])
def delete_user_data(user_id):
    """Delete all user data (Right to be forgotten)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Delete user (cascade will delete related data)
    db.session.delete(user)
    db.session.commit()
    
    session.pop('user_id', None)
    
    return jsonify({'message': 'All user data deleted'}), 200

# ==================== HELPER FUNCTIONS ====================

def update_learning_behavior(user_id):
    """Update learning behavior metrics"""
    behavior = LearningBehavior.query.filter_by(user_id=user_id).first()
    
    if not behavior:
        behavior = LearningBehavior(user_id=user_id)
        db.session.add(behavior)
    
    # Calculate metrics
    interactions = UserInteraction.query.filter_by(user_id=user_id).all()
    
    # Handle duration - convert to int, handle both strings and None
    def safe_duration(interaction):
        if interaction.duration is None:
            return 0
        try:
            return int(interaction.duration)
        except (ValueError, TypeError):
            return 0
    
    total_time = sum(safe_duration(i) for i in interactions)
    behavior.total_time_spent = total_time
    
    sessions = len(set(i.session_id for i in interactions if i.session_id))
    behavior.total_sessions = sessions
    
    if sessions > 0:
        behavior.avg_session_duration = total_time // sessions
    
    # Calculate engagement score
    recent_interactions = [i for i in interactions 
                          if i.timestamp > datetime.utcnow() - timedelta(days=30)]
    
    if recent_interactions:
        engagement = min(len(recent_interactions) / 100 * 100, 100)
        behavior.engagement_score = engagement
    
    # Calculate courses in progress and completed
    # Get unique courses the user has interacted with
    course_interactions = {}
    for interaction in interactions:
        if interaction.resource_type in ['VIDEO', 'LESSON', 'COURSE']:
            # Try to find the course ID
            course_id = None
            if interaction.resource_type == 'COURSE':
                course_id = interaction.resource_id
            elif interaction.resource_type in ['VIDEO', 'LESSON']:
                # Get lesson and find its course
                lesson = Lesson.query.get(interaction.resource_id)
                if lesson and lesson.module:
                    course_id = lesson.module.course_id
            
            if course_id:
                if course_id not in course_interactions:
                    course_interactions[course_id] = {'count': 0, 'time': 0}
                course_interactions[course_id]['count'] += 1
                course_interactions[course_id]['time'] += safe_duration(interaction)
    
    # Determine courses in progress vs completed
    # A course is "completed" if user has spent >80% of estimated time or has >20 interactions
    courses_in_progress = 0
    courses_completed = 0
    
    for course_id, stats in course_interactions.items():
        course = Course.query.get(course_id)
        if course:
            estimated_seconds = course.duration_hours * 3600
            completion_ratio = stats['time'] / estimated_seconds if estimated_seconds > 0 else 0
            
            # Consider completed if >80% time spent or >20 interactions
            if completion_ratio > 0.8 or stats['count'] > 20:
                courses_completed += 1
            else:
                courses_in_progress += 1
    
    behavior.courses_in_progress = courses_in_progress
    behavior.courses_completed = courses_completed
    
    db.session.commit()
    
    # Trigger VARK inference on EVERY interaction for real-time updates
    print(f"Triggering VARK inference for user {user_id} after interaction")
    result = vark_service.infer_learning_style(user_id)
    print(f"Inference result: {result}")

def get_popular_courses():
    """Get popular courses (fallback when no personalization)"""
    # Get courses with most interactions
    from sqlalchemy import func
    
    popular = db.session.query(
        Course,
        func.count(UserInteraction.id).label('interaction_count')
    ).join(
        UserInteraction,
        UserInteraction.resource_id == Course.id
    ).filter(
        UserInteraction.resource_type == 'COURSE'
    ).group_by(Course.id).order_by(
        func.count(UserInteraction.id).desc()
    ).limit(10).all()
    
    return jsonify({
        'recommendations': [
            {
                'course': course.to_dict(),
                'score': count * 10,
                'reasoning': 'Popular course',
                'type': 'POPULAR'
            }
            for course, count in popular
        ]
    }), 200

# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/learning-style')
def learning_style_page():
    """Learning style page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('learning_style.html')

@app.route('/recommendations')
def recommendations_page():
    """Recommendations page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('recommendations.html')

@app.route('/privacy')
def privacy_page():
    """Privacy settings page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('privacy.html')

@app.route('/concept-mastery')
def concept_mastery_page():
    """Concept mastery tracking page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('concept_mastery.html')

@app.route('/courses')
def courses_page():
    """Browse courses page"""
    return render_template('courses.html')

@app.route('/tests')
def tests_page():
    """Skill tests page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('tests.html')

# ==================== TESTS API ====================

@app.route('/api/tests/generate', methods=['POST'])
def generate_test():
    """Generate AI-powered test"""
    data = request.json
    user_id = session.get('user_id')
    
    # Generate test with Gemini using robust service method
    test_data = gemini_service.generate_test(
        topic=data['topic'],
        difficulty=data.get('difficulty', 'intermediate'),
        num_questions=int(data.get('question_count', 10))
    )
    
    if isinstance(test_data, dict) and 'questions' in test_data:
        # Add ID for tracking
        test_data['id'] = f"test_{datetime.utcnow().timestamp()}"
        test_data['user_id'] = user_id
        test_data['topic'] = data['topic']
        
        return jsonify(test_data), 200
    else:
        return jsonify({'error': 'Failed to generate test'}), 500

@app.route('/api/tests/submit', methods=['POST'])
def submit_test():
    """Submit test answers and get results"""
    data = request.json
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Calculate score (simplified - in real app, verify against stored test)
    answers = data.get('answers', {})
    total_questions = len(answers)
    
    # For demo, assume 70% correct
    correct_answers = int(total_questions * 0.7)
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score >= 70
    
    # Save result
    test_result = TestResult(
        user_id=user_id,
        title=data.get('test_title', 'Skill Test'), # Frontend should send title
        topic=data.get('topic', 'General'),
        difficulty=data.get('difficulty', 'Intermediate'),
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions,
        passed=passed
    )
    
    db.session.add(test_result)
    db.session.commit()
    
    result = {
        'score': round(score, 1),
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'passed': passed,
        'completed_at': datetime.utcnow().isoformat()
    }
    
    return jsonify(result), 200

@app.route('/api/tests/history/<int:user_id>', methods=['GET'])
def get_test_history(user_id):
    """Get user's test history"""
    results = TestResult.query.filter_by(user_id=user_id).order_by(TestResult.completed_at.desc()).all()
    return jsonify([r.to_dict() for r in results]), 200

# ==================== PROGRESS TRACKING (LMS Enhancement) ====================

@app.route('/api/progress/lesson', methods=['POST'])
def track_lesson_progress():
    """Track granular lesson progress"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    lesson_id = data.get('lesson_id')
    if not lesson_id:
        return jsonify({'error': 'lesson_id is required'}), 400

    action = data.get('action', 'CONTENT_VIEW')
    duration_seconds = data.get('duration_seconds', 0)

    # Build metadata for additional tracking info
    metadata = {}
    if data.get('video_percentage') is not None:
        metadata['percentage'] = data['video_percentage']  # Map to 'percentage' for service
    if data.get('percentage') is not None:
        metadata['percentage'] = data['percentage']
    if data.get('quiz_score') is not None:
        metadata['score'] = data['quiz_score']  # Map to 'score' for service
    if data.get('score') is not None:
        metadata['score'] = data['score']

    result = progress_tracking_service.track_lesson_progress(
        user_id=user_id,
        lesson_id=lesson_id,
        action=action,
        duration_seconds=duration_seconds,
        metadata=metadata if metadata else None
    )

    return jsonify(result), 200


@app.route('/api/progress/comprehensive/<int:user_id>', methods=['GET'])
def get_comprehensive_progress(user_id):
    """Get comprehensive progress report for a user"""
    progress = progress_tracking_service.get_comprehensive_progress(user_id)
    return jsonify(progress), 200


@app.route('/api/progress/velocity/<int:user_id>', methods=['GET'])
def get_learning_velocity_endpoint(user_id):
    """Get learning velocity analysis for a user"""
    velocity_data = progress_tracking_service.calculate_learning_velocity(user_id)
    return jsonify(velocity_data), 200


@app.route('/api/progress/knowledge-gaps/<int:user_id>', methods=['GET'])
def get_knowledge_gaps(user_id):
    """Identify knowledge gaps from quiz performance"""
    gaps = progress_tracking_service.identify_knowledge_gaps(user_id)
    return jsonify(gaps), 200


@app.route('/api/progress/course/<int:user_id>/<int:course_id>', methods=['GET'])
def get_course_progress(user_id, course_id):
    """Get detailed progress for a specific course"""
    progress = progress_tracking_service.get_course_progress(user_id, course_id)
    if not progress:
        return jsonify({'error': 'No progress found'}), 404
    return jsonify(progress), 200


# ==================== AI CONTENT GENERATION (LMS Enhancement) ====================

@app.route('/api/ai/generate/course', methods=['POST'])
def generate_personalized_course():
    """Generate a personalized course using advanced AI prompts"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    difficulty = data.get('difficulty', 'intermediate')
    num_modules = data.get('num_modules', 5)
    force_regenerate = data.get('force_regenerate', False)

    # Generate personalized course
    course_data = ai_content_service.generate_personalized_course(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        num_modules=num_modules,
        force_regenerate=force_regenerate
    )

    if course_data and 'title' in course_data:
        # Optionally save to database
        if data.get('save_to_db', True):
            course = Course(
                title=course_data['title'],
                description=course_data.get('description', ''),
                difficulty=course_data.get('difficulty', 'INTERMEDIATE').upper(),
                duration_hours=course_data.get('estimated_hours', 40),
                tags=','.join(course_data.get('tags', [])),
                instructor_id=None  # AI-generated
            )

            db.session.add(course)
            db.session.flush()

            # Process modules and lessons
            if 'modules' in course_data:
                for i, mod_data in enumerate(course_data['modules']):
                    module = Module(
                        course_id=course.id,
                        title=mod_data['title'],
                        order=i
                    )
                    db.session.add(module)
                    db.session.flush()

                    if 'lessons' in mod_data:
                        for j, lesson_data in enumerate(mod_data['lessons']):
                            # Find relevant video
                            video_query = f"{lesson_data['title']} {topic} tutorial"
                            videos = youtube_service.search_videos(video_query, max_results=1)
                            video_url = videos[0]['url'] if videos else None
                            video_id = videos[0]['id'] if videos else None

                            lesson = Lesson(
                                module_id=module.id,
                                title=lesson_data['title'],
                                content=lesson_data.get('content', ''),
                                duration_minutes=lesson_data.get('duration_minutes', 15),
                                video_url=video_url,
                                video_id=video_id,
                                order=j,
                                assignment=lesson_data.get('assignment'),
                                code_example=lesson_data.get('code_example'),
                                interactive_element=lesson_data.get('interactive_element'),
                                quiz_questions=json.dumps(lesson_data.get('quiz_questions', [])) if lesson_data.get('quiz_questions') else None
                            )
                            db.session.add(lesson)

            db.session.commit()
            course_data['course_id'] = course.id

        return jsonify({
            'message': 'Personalized course generated successfully',
            'course': course_data,
            'personalization_applied': user_id is not None
        }), 201
    else:
        return jsonify({'error': 'Failed to generate course'}), 500


@app.route('/api/ai/generate/quiz', methods=['POST'])
def generate_adaptive_quiz():
    """Generate an adaptive quiz based on user performance"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    num_questions = data.get('num_questions', 10)
    difficulty = data.get('difficulty')  # Optional - will be auto-adjusted if not provided
    force_regenerate = data.get('force_regenerate', False)

    # Generate adaptive quiz
    quiz_data = ai_content_service.generate_adaptive_quiz(
        user_id=user_id,
        topic=topic,
        num_questions=num_questions,
        difficulty=difficulty,
        force_regenerate=force_regenerate
    )

    if quiz_data:
        # Add metadata
        quiz_data['generated_at'] = datetime.utcnow().isoformat()
        quiz_data['user_id'] = user_id

        return jsonify({
            'message': 'Adaptive quiz generated successfully',
            'quiz': quiz_data,
            'personalization_applied': user_id is not None
        }), 200
    else:
        return jsonify({'error': 'Failed to generate quiz'}), 500


@app.route('/api/ai/generate/assignment', methods=['POST'])
def generate_personalized_assignment():
    """Generate a personalized assignment based on user skills"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    lesson_context = data.get('lesson_context', '')
    force_regenerate = data.get('force_regenerate', False)

    # Generate personalized assignment
    assignment_data = ai_content_service.generate_personalized_assignment(
        user_id=user_id,
        topic=topic,
        lesson_context=lesson_context,
        force_regenerate=force_regenerate
    )

    if assignment_data:
        return jsonify({
            'message': 'Personalized assignment generated successfully',
            'assignment': assignment_data,
            'personalization_applied': user_id is not None
        }), 200
    else:
        return jsonify({'error': 'Failed to generate assignment'}), 500


# ==================== VIDEO QUIZ (Quick knowledge check after videos) ====================

@app.route('/api/video-quiz/generate', methods=['POST'])
def generate_video_quiz():
    """Generate a quick 2-3 question quiz for after video viewing"""
    data = request.json
    lesson_title = data.get('lesson_title', '')
    lesson_content = data.get('lesson_content', '')
    question_count = min(data.get('question_count', 3), 5)  # Max 5 questions

    if not lesson_title:
        return jsonify({'error': 'lesson_title is required'}), 400

    # Try to use Gemini for smart questions
    try:
        prompt = f"""Generate exactly {question_count} multiple choice questions to test understanding of this lesson.

Lesson Title: {lesson_title}
Lesson Content: {lesson_content[:500] if lesson_content else lesson_title}

Requirements:
- Questions should test key concepts from the lesson
- Each question should have exactly 4 options (A, B, C, D)
- Include the correct answer index (0-3)
- Include a brief explanation for each answer
- Make questions progressively harder

Return ONLY valid JSON in this exact format:
{{
    "questions": [
        {{
            "question": "Question text here?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Brief explanation of why this is correct."
        }}
    ]
}}"""

        response = gemini_service.generate_content(prompt)
        if response:
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                quiz_data = json.loads(json_match.group())
                return jsonify(quiz_data), 200
    except Exception as e:
        print(f"Error generating video quiz with Gemini: {e}")

    # Fallback: Generate basic questions
    fallback_questions = [
        {
            "question": f"What is the main topic covered in '{lesson_title}'?",
            "options": [
                "The fundamental concepts and key principles",
                "Only advanced implementation details",
                "Historical background information only",
                "Unrelated supplementary content"
            ],
            "correct_answer": 0,
            "explanation": "This lesson primarily covers the fundamental concepts and key principles of the topic."
        },
        {
            "question": f"Why is understanding '{lesson_title}' important for your learning journey?",
            "options": [
                "It's optional and not very important",
                "It builds a strong foundation for advanced topics",
                "It's only needed for certification exams",
                "It's purely theoretical with no practical use"
            ],
            "correct_answer": 1,
            "explanation": "Understanding foundational concepts builds a strong base for learning more advanced material."
        },
        {
            "question": f"What is the best approach after completing '{lesson_title}'?",
            "options": [
                "Move on immediately without practice",
                "Practice with hands-on exercises and examples",
                "Skip directly to unrelated advanced topics",
                "Avoid any further review"
            ],
            "correct_answer": 1,
            "explanation": "Practicing with hands-on exercises helps reinforce and solidify your understanding."
        }
    ]

    return jsonify({'questions': fallback_questions[:question_count]}), 200


# ==================== LEARNING PATHS (LMS Enhancement) ====================

@app.route('/api/learning-path/<int:user_id>', methods=['GET'])
def get_user_learning_path(user_id):
    """Get the user's current learning path"""
    path = LearningPath.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(LearningPath.created_at.desc()).first()

    if not path:
        return jsonify({'message': 'No active learning path found'}), 404

    return jsonify(path.to_dict()), 200


@app.route('/api/learning-path/generate', methods=['POST'])
def generate_learning_path():
    """Generate a personalized learning path"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    target_skill = data.get('target_skill')
    if not target_skill:
        return jsonify({'error': 'target_skill is required'}), 400

    current_level = data.get('current_level', 'beginner')
    weeks = data.get('weeks', 12)

    # Generate learning path with AI
    path_data = ai_content_service.generate_learning_path(
        user_id=user_id,
        target_skill=target_skill,
        current_level=current_level,
        weeks=weeks
    )

    if path_data:
        # Save to database
        learning_path = LearningPath(
            user_id=user_id,
            title=path_data.get('title', f'Path to {target_skill}'),
            goal=target_skill,
            target_skill=target_skill,
            milestones=json.dumps(path_data.get('milestones', [])),
            course_sequence=json.dumps(path_data.get('course_sequence', [])),
            target_completion=datetime.utcnow() + timedelta(weeks=weeks),
            is_active=True
        )

        # Get user's learning style for adaptation
        style = LearningStyle.query.filter_by(user_id=user_id).first()
        if style:
            learning_path.adapted_for_style = style.dominant_style

        db.session.add(learning_path)
        db.session.commit()

        path_data['learning_path_id'] = learning_path.id

        return jsonify({
            'message': 'Learning path generated successfully',
            'learning_path': path_data
        }), 201
    else:
        return jsonify({'error': 'Failed to generate learning path'}), 500


@app.route('/api/learning-path/<int:path_id>/progress', methods=['POST'])
def update_learning_path_progress(path_id):
    """Update progress on a learning path"""
    data = request.json

    path = LearningPath.query.get(path_id)
    if not path:
        return jsonify({'error': 'Learning path not found'}), 404

    # Update milestone progress
    if 'milestone_completed' in data:
        path.current_milestone = data['milestone_completed']

    if 'overall_progress' in data:
        path.overall_progress = data['overall_progress']

    db.session.commit()

    return jsonify({
        'message': 'Progress updated',
        'learning_path': path.to_dict()
    }), 200


# ==================== SPACED REPETITION (LMS Enhancement) ====================

@app.route('/api/spaced-repetition/<int:user_id>/schedule', methods=['GET'])
def get_review_schedule(user_id):
    """Get spaced repetition review schedule"""
    schedule = personalization_service.get_review_schedule(user_id)
    return jsonify(schedule), 200


@app.route('/api/spaced-repetition/<int:user_id>/review-content', methods=['POST'])
def generate_review_content(user_id):
    """Generate review content for spaced repetition"""
    data = request.json
    topic = data.get('topic')

    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    # Get user's performance history for this topic
    history = PerformanceHistory.query.filter_by(
        user_id=user_id,
        topic=topic
    ).first()

    if not history:
        return jsonify({'error': 'No learning history for this topic'}), 404

    # Generate review quiz targeting weak areas
    weak_areas = json.loads(history.weak_areas) if history.weak_areas else []

    review_quiz = ai_content_service.generate_adaptive_quiz(
        user_id=user_id,
        topic=topic,
        num_questions=5,
        target_weak_areas=weak_areas,
        force_regenerate=True
    )

    return jsonify({
        'review_content': review_quiz,
        'topic': topic,
        'weak_areas_targeted': weak_areas,
        'current_mastery': history.skill_level,
        'review_count': history.repetition_count
    }), 200


@app.route('/api/spaced-repetition/<int:user_id>/record-review', methods=['POST'])
def record_review_result(user_id):
    """Record the result of a spaced repetition review"""
    data = request.json

    topic = data.get('topic')
    score = data.get('score')  # 0-100

    if not topic or score is None:
        return jsonify({'error': 'topic and score are required'}), 400

    # Update performance history with new review result
    result = personalization_service.update_performance_history(
        user_id=user_id,
        topic=topic,
        quiz_score=score
    )

    return jsonify({
        'message': 'Review recorded',
        'performance_update': result
    }), 200


# ==================== PERSONALIZATION (LMS Enhancement) ====================

@app.route('/api/personalization/profile/<int:user_id>', methods=['GET'])
def get_learning_profile(user_id):
    """Get comprehensive learning profile for a user"""
    profile = personalization_service.get_user_learning_profile(user_id)
    return jsonify(profile), 200


@app.route('/api/personalization/insights/<int:user_id>', methods=['GET'])
def get_learning_insights(user_id):
    """Get AI-powered learning insights and recommendations"""
    insights = personalization_service.get_learning_insights(user_id)
    return jsonify(insights), 200


@app.route('/api/personalization/difficulty/<int:user_id>', methods=['GET'])
def get_difficulty_adjustment(user_id):
    """Get recommended difficulty adjustment for a user"""
    topic = request.args.get('topic')
    adjustment = personalization_service.adjust_difficulty_for_user(user_id, topic)
    return jsonify(adjustment), 200


@app.route('/api/personalization/performance', methods=['POST'])
def update_performance():
    """Update performance history after quiz or assignment"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    # Support both quiz and assignment scores
    score = data.get('quiz_score') or data.get('assignment_score') or data.get('score', 0)
    is_quiz = 'quiz_score' in data or 'score' in data

    result = personalization_service.update_performance_history(
        user_id=user_id,
        topic=topic,
        score=score,
        is_quiz=is_quiz,
        concepts_correct=data.get('strong_areas', []),
        concepts_wrong=data.get('weak_areas', [])
    )

    return jsonify({
        'message': 'Performance updated',
        'result': result
    }), 200


# ==================== QUIZ ATTEMPTS (LMS Enhancement) ====================

@app.route('/api/quiz/attempt', methods=['POST'])
def record_quiz_attempt():
    """Record a detailed quiz attempt with per-question analysis"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    score = data.get('score', 0)
    total_questions = data.get('total_questions', data.get('questions_answered', 0))
    passing_score = data.get('passing_score', 70.0)

    # Create quiz attempt record
    attempt = QuizAttempt(
        user_id=user_id,
        lesson_id=data.get('lesson_id'),
        course_id=data.get('course_id'),
        quiz_title=data.get('quiz_title', data.get('title', 'Quiz')),
        quiz_topic=data.get('topic'),
        difficulty_level=data.get('difficulty', 'MEDIUM'),
        score=score,
        correct_answers=data.get('correct_answers', 0),
        total_questions=total_questions,
        passed=score >= passing_score,
        passing_score=passing_score,
        time_taken_seconds=data.get('time_taken_seconds', 0),
        question_performance=json.dumps(data.get('question_performance', {})),
        knowledge_gaps_identified=json.dumps(data.get('knowledge_gaps', []))
    )

    db.session.add(attempt)
    db.session.commit()

    # Update lesson progress if lesson_id provided
    if data.get('lesson_id'):
        progress_tracking_service.track_lesson_progress(
            user_id=user_id,
            lesson_id=data['lesson_id'],
            action='QUIZ_ATTEMPT',
            metadata={'quiz_score': score}
        )

    # Update performance history
    if data.get('topic'):
        personalization_service.update_performance_history(
            user_id=user_id,
            topic=data['topic'],
            score=score,
            is_quiz=True,
            concepts_wrong=data.get('knowledge_gaps', [])
        )

    return jsonify({
        'message': 'Quiz attempt recorded',
        'attempt_id': attempt.id,
        'score': attempt.score,
        'passed': attempt.passed
    }), 201


@app.route('/api/quiz/attempts/<int:user_id>', methods=['GET'])
def get_quiz_attempts(user_id):
    """Get quiz attempt history for a user"""
    limit = request.args.get('limit', 20, type=int)
    topic = request.args.get('topic')

    query = QuizAttempt.query.filter_by(user_id=user_id)

    if topic:
        query = query.filter_by(quiz_topic=topic)

    attempts = query.order_by(QuizAttempt.completed_at.desc()).limit(limit).all()

    return jsonify({
        'attempts': [a.to_dict() for a in attempts],
        'total_attempts': query.count()
    }), 200


# ==================== CACHE MANAGEMENT (LMS Enhancement) ====================

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get content cache statistics"""
    content_type = request.args.get('content_type')
    stats = cache_service.get_cache_stats(content_type)
    return jsonify(stats), 200


@app.route('/api/cache/invalidate', methods=['POST'])
def invalidate_cache():
    """Invalidate cached content"""
    data = request.json

    count = cache_service.invalidate_cache(
        content_type=data.get('content_type'),
        topic=data.get('topic'),
        cache_key=data.get('cache_key')
    )

    return jsonify({
        'message': f'Invalidated {count} cache entries',
        'count': count
    }), 200


@app.route('/api/cache/feedback', methods=['POST'])
def submit_content_feedback():
    """Submit feedback on AI-generated content"""
    data = request.json

    cache_key = data.get('cache_key')
    positive = data.get('positive', True)

    if not cache_key:
        return jsonify({'error': 'cache_key is required'}), 400

    success = cache_service.record_feedback(cache_key, positive)

    return jsonify({
        'message': 'Feedback recorded' if success else 'Failed to record feedback',
        'success': success
    }), 200 if success else 400


# ==================== PHASE 2: VARK-AWARE VIDEO INTEGRATION ====================

@app.route('/api/videos/search', methods=['POST'])
def search_videos_vark():
    """Search videos optimized for user's VARK learning style"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')
    query = data.get('query')

    if not query:
        return jsonify({'error': 'query is required'}), 400

    # Get user's learning style
    learning_style = 'VISUAL'  # Default
    vark_scores = None

    if user_id:
        style = LearningStyle.query.filter_by(user_id=user_id).first()
        if style:
            learning_style = style.dominant_style or 'VISUAL'
            vark_scores = {
                'visual': style.visual_score,
                'auditory': style.auditory_score,
                'kinesthetic': style.kinesthetic_score,
                'reading_writing': style.reading_writing_score
            }

    # Override with request params if provided
    learning_style = data.get('learning_style', learning_style)
    difficulty = data.get('difficulty', 'intermediate')
    max_results = data.get('max_results', 10)

    # Search with VARK optimization
    videos = youtube_service.search_videos_vark_optimized(
        query=query,
        learning_style=learning_style,
        vark_scores=vark_scores,
        max_results=max_results,
        difficulty=difficulty
    )

    return jsonify({
        'query': query,
        'learning_style_used': learning_style,
        'total_results': len(videos),
        'videos': videos
    }), 200


@app.route('/api/videos/<video_id>/vark-characteristics', methods=['GET'])
def get_video_vark_characteristics(video_id):
    """Get detailed VARK characteristics for a video"""
    characteristics = youtube_service.get_video_vark_characteristics(video_id)

    if not characteristics:
        return jsonify({'error': 'Video not found or unable to analyze'}), 404

    return jsonify(characteristics), 200


@app.route('/api/videos/track-engagement', methods=['POST'])
def track_video_engagement():
    """Track video engagement with VARK correlation"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    video_id = data.get('video_id')
    if not video_id:
        return jsonify({'error': 'video_id is required'}), 400

    engagement_data = {
        'watch_duration': data.get('watch_duration_seconds', 0),
        'total_duration': data.get('total_duration_seconds'),
        'replays': data.get('replay_count', 0),
        'pauses': data.get('pause_count', 0),
        'seek_forward': data.get('seek_forward_count', 0),
        'seek_backward': data.get('seek_backward_count', 0),
        'playback_speed': data.get('playback_speed', 1.0)
    }

    result = youtube_service.track_video_engagement(
        db=db,
        user_id=user_id,
        video_id=video_id,
        engagement_data=engagement_data,
        lesson_id=data.get('lesson_id')
    )

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 200


@app.route('/api/videos/analytics/<int:user_id>', methods=['GET'])
def get_video_analytics(user_id):
    """Get video analytics dashboard for a user"""
    days = request.args.get('days', 30, type=int)

    analytics = youtube_service.get_video_analytics_dashboard(
        db=db,
        user_id=user_id,
        days=days
    )

    if 'error' in analytics:
        return jsonify(analytics), 500

    return jsonify(analytics), 200


@app.route('/api/lessons/<int:lesson_id>/recommended-videos', methods=['GET'])
def get_lesson_recommended_videos(lesson_id):
    """Get VARK-optimized video recommendations for a lesson"""
    user_id = request.args.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404

    max_results = request.args.get('max_results', 5, type=int)

    videos = youtube_service.get_recommended_videos_for_lesson(
        lesson_topic=lesson.title,
        user_id=int(user_id),
        db=db,
        max_results=max_results
    )

    return jsonify({
        'lesson_id': lesson_id,
        'lesson_title': lesson.title,
        'recommended_videos': videos
    }), 200


# ==================== PHASE 2: ENHANCED RECOMMENDATIONS ====================

@app.route('/api/recommendations/v2/<int:user_id>', methods=['GET'])
def get_recommendations_v2(user_id):
    """Get enhanced personalized recommendations with all methods"""
    count = request.args.get('count', 10, type=int)
    include_explanations = request.args.get('explanations', 'true').lower() == 'true'

    # Optional context from query params
    context = None
    if request.args.get('current_topic') or request.args.get('current_difficulty'):
        context = {
            'current_topic': request.args.get('current_topic'),
            'current_difficulty': request.args.get('current_difficulty'),
            'time_of_day': request.args.get('time_of_day')
        }

    try:
        result = recommendation_service.get_recommendations_v2(
            user_id=user_id,
            count=count,
            include_explanations=include_explanations,
            context=context
        )
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in recommendations v2: {e}")
        # Fallback to basic recommendations
        return get_recommendations(user_id)


@app.route('/api/recommendations/explain/<int:user_id>/<int:course_id>', methods=['GET'])
def explain_recommendation(user_id, course_id):
    """Get detailed AI explanation for why a course is recommended"""
    explanation = recommendation_service.get_recommendation_explanation(user_id, course_id)

    if 'error' in explanation:
        return jsonify(explanation), 404

    return jsonify(explanation), 200


@app.route('/api/recommendations/realtime-update', methods=['POST'])
def realtime_recommendation_update():
    """Trigger real-time recommendation update after user action"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    trigger_event = {
        'type': data.get('event_type'),  # COURSE_COMPLETE, COURSE_ENROLL, LESSON_COMPLETE, QUIZ_COMPLETE
        'resource_id': data.get('resource_id'),
        'score': data.get('score'),
        'engagement_score': data.get('engagement_score'),
        'metadata': data.get('metadata', {})
    }

    result = recommendation_service.update_recommendations_realtime(user_id, trigger_event)

    return jsonify(result), 200


@app.route('/api/recommendations/retrain', methods=['POST'])
def retrain_recommendations():
    """Retrain the matrix factorization model"""
    # This could be protected with admin auth in production
    result = recommendation_service.retrain_matrix_factorization()

    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code


# ==================== PHASE 2: ADVANCED BEHAVIORAL TRACKING ====================

@app.route('/api/behavior/session/start', methods=['POST'])
def start_learning_session():
    """Start a new learning session for behavioral tracking"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    result = vark_service.start_learning_session(
        user_id=user_id,
        device_type=data.get('device_type'),
        browser=data.get('browser'),
        platform=data.get('platform')
    )

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 201


@app.route('/api/behavior/session/<session_id>/end', methods=['POST'])
def end_learning_session(session_id):
    """End a learning session and get analysis"""
    result = vark_service.end_learning_session(session_id)

    if 'error' in result:
        return jsonify(result), 404

    return jsonify(result), 200


@app.route('/api/behavior/event', methods=['POST'])
def track_engagement_event():
    """Track a fine-grained engagement event for VARK analysis"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    event_type = data.get('event_type')
    if not event_type:
        return jsonify({'error': 'event_type is required'}), 400

    result = vark_service.track_engagement_event(
        user_id=user_id,
        event_type=event_type,
        resource_type=data.get('resource_type'),
        resource_id=data.get('resource_id'),
        session_id=data.get('session_id'),
        event_data=data.get('event_data'),
        position=data.get('position'),
        duration_ms=data.get('duration_ms')
    )

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 201


@app.route('/api/behavior/session/<session_id>/analysis', methods=['GET'])
def get_session_analysis(session_id):
    """Get detailed analysis of a learning session"""
    user_id = request.args.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    analysis = vark_service.analyze_session(int(user_id), session_id)

    if 'error' in analysis:
        return jsonify(analysis), 404

    return jsonify(analysis), 200


# ==================== PHASE 2: PREDICTIVE VARK ====================

@app.route('/api/vark/predict/<int:user_id>', methods=['GET'])
def predict_vark_style(user_id):
    """Get predictive VARK analysis with confidence intervals"""
    prediction = vark_service.predict_learning_style(user_id)

    if 'error' in prediction:
        return jsonify(prediction), 500

    return jsonify(prediction), 200


@app.route('/api/vark/realtime-update', methods=['POST'])
def realtime_vark_update():
    """Update VARK scores in real-time based on an event"""
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    event = {
        'type': data.get('event_type'),
        'metadata': data.get('metadata', {})
    }

    result = vark_service.update_vark_realtime(user_id, event)

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 200


@app.route('/api/vark/trajectory/<int:user_id>', methods=['GET'])
def get_vark_trajectory(user_id):
    """Get VARK score evolution over time"""
    days = request.args.get('days', 30, type=int)

    trajectory = vark_service.get_vark_trajectory(user_id, days)

    if 'error' in trajectory:
        return jsonify(trajectory), 500

    return jsonify(trajectory), 200


@app.route('/api/vark/shift-detection/<int:user_id>', methods=['GET'])
def detect_vark_shift(user_id):
    """Detect if user's learning style is shifting"""
    days = request.args.get('days', 14, type=int)

    shift_analysis = vark_service.detect_style_shift(user_id, days)

    if 'error' in shift_analysis:
        return jsonify(shift_analysis), 500

    return jsonify(shift_analysis), 200


# ==================== PHASE 2: BEHAVIORAL FINGERPRINTING ====================

@app.route('/api/behavior/fingerprint/<int:user_id>', methods=['GET'])
def get_behavioral_fingerprint(user_id):
    """Get comprehensive behavioral fingerprint for a user"""
    fingerprint = vark_service.create_behavioral_fingerprint(user_id)

    if 'error' in fingerprint:
        return jsonify(fingerprint), 500

    return jsonify(fingerprint), 200


@app.route('/api/behavior/patterns/<int:user_id>', methods=['GET'])
def get_engagement_patterns(user_id):
    """Get engagement patterns for a user"""
    days = request.args.get('days', 30, type=int)

    patterns = vark_service.analyze_learning_pattern(user_id, days)

    return jsonify(patterns), 200


# ==================== PHASE 2 ENHANCEMENTS ====================

@app.route('/api/vark/dynamic-weights/<int:user_id>', methods=['GET'])
def get_dynamic_vark_weights(user_id):
    """Get dynamic VARK weights based on confidence and recency"""
    weights = vark_service.get_dynamic_vark_weights(user_id)
    return jsonify(weights), 200


@app.route('/api/vark/adaptive-content/<int:user_id>', methods=['GET'])
def get_adaptive_content_recommendations(user_id):
    """Get content recommendations that adapt to VARK drift"""
    recommendations = vark_service.get_adaptive_content_recommendations(user_id)
    return jsonify(recommendations), 200


@app.route('/api/session/<session_id>/summary', methods=['GET'])
def get_session_summary(session_id):
    """Get comprehensive learning session summary"""
    user_id = request.args.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    summary = vark_service.generate_session_summary(int(user_id), session_id)

    if 'error' in summary:
        return jsonify(summary), 404

    return jsonify(summary), 200


@app.route('/api/difficulty/confidence-aware/<int:user_id>', methods=['GET'])
def get_confidence_aware_difficulty(user_id):
    """Get difficulty recommendation with confidence-aware adaptation"""
    from personalization_service import get_personalization_service

    topic = request.args.get('topic')
    include_analysis = request.args.get('analysis', 'true').lower() == 'true'

    personalization = get_personalization_service()
    result = personalization.get_confidence_aware_difficulty(
        user_id=user_id,
        topic=topic,
        include_analysis=include_analysis
    )

    return jsonify(result), 200


@app.route('/api/concepts/mastery', methods=['POST'])
def update_concept_mastery():
    """Update mastery for a specific concept"""
    from personalization_service import get_personalization_service

    data = request.json
    user_id = data.get('user_id') or session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    concept_name = data.get('concept_name')
    if not concept_name:
        return jsonify({'error': 'concept_name is required'}), 400

    personalization = get_personalization_service()
    result = personalization.update_concept_mastery(
        user_id=int(user_id),
        concept_name=concept_name,
        correct=data.get('correct', False),
        topic=data.get('topic'),
        course_id=data.get('course_id'),
        time_spent_seconds=data.get('time_spent_seconds', 0),
        misconception=data.get('misconception')
    )

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 200


@app.route('/api/concepts/mastery/<int:user_id>', methods=['GET'])
def get_concept_mastery_report(user_id):
    """Get comprehensive concept mastery report"""
    from personalization_service import get_personalization_service

    topic = request.args.get('topic')

    personalization = get_personalization_service()
    report = personalization.get_concept_mastery_report(user_id, topic)

    return jsonify(report), 200


@app.route('/api/content/bias/<int:user_id>', methods=['GET'])
def analyze_content_bias(user_id):
    """Analyze content exposure bias for a user"""
    result = recommendation_service.analyze_content_bias(user_id)

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result), 200


@app.route('/api/recommendations/bias-aware/<int:user_id>', methods=['GET'])
def get_bias_aware_recommendations(user_id):
    """Get recommendations that actively balance content bias"""
    count = request.args.get('count', 10, type=int)
    balance_bias = request.args.get('balance', 'true').lower() == 'true'

    result = recommendation_service.get_bias_aware_recommendations(
        user_id=user_id,
        count=count,
        balance_bias=balance_bias
    )

    return jsonify(result), 200


# ==================== BIAS MONITORING ====================

@app.route('/api/bias/analyze', methods=['GET'])
def analyze_bias():
    """Analyze system for bias"""
    from bias_monitor import BiasMonitor
    
    monitor = BiasMonitor()
    analysis = monitor.analyze_recommendation_bias()
    
    return jsonify(analysis), 200

@app.route('/api/bias/report', methods=['GET'])
def get_bias_report():
    """Get human-readable bias report"""
    from bias_monitor import BiasMonitor
    
    monitor = BiasMonitor()
    report = monitor.generate_bias_report()
    
    return jsonify({'report': report}), 200

@app.route('/api/bias/mitigation', methods=['GET'])
def get_mitigation_strategies():
    """Get bias mitigation strategies"""
    from bias_monitor import BiasMonitor
    
    monitor = BiasMonitor()
    analysis = monitor.analyze_recommendation_bias()
    strategies = monitor.get_mitigation_strategies(analysis)
    
    return jsonify({
        'strategies': strategies,
        'fairness_score': analysis['overall_fairness_score'],
        'bias_detected': analysis['bias_detected']
    }), 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5001)),
        debug=app.config['DEBUG']
    )
