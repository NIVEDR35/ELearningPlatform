from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='STUDENT')  # STUDENT, INSTRUCTOR, ADMIN
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    interactions = db.relationship('UserInteraction', backref='user', lazy=True, cascade='all, delete-orphan')
    learning_behavior = db.relationship('LearningBehavior', backref='user', uselist=False, cascade='all, delete-orphan')
    learning_style = db.relationship('LearningStyle', backref='user', uselist=False, cascade='all, delete-orphan')
    consent = db.relationship('UserConsent', backref='user', uselist=False, cascade='all, delete-orphan')
    recommendations = db.relationship('CourseRecommendation', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Course(db.Model):
    """Course model"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20))  # BEGINNER, INTERMEDIATE, ADVANCED
    duration_hours = db.Column(db.Integer)
    tags = db.Column(db.String(500))  # Comma-separated tags
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'duration_hours': self.duration_hours,
            'tags': self.tags.split(',') if self.tags else [],
            'instructor_id': self.instructor_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modules': [m.to_dict() for m in self.modules]
        }

    def to_summary_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'duration_hours': self.duration_hours,
            'tags': self.tags.split(',') if self.tags else [],
            'instructor_id': self.instructor_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'module_count': len(self.modules)
        }

class Module(db.Model):
    """Course module"""
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)
    
    # Relationships
    course = db.relationship('Course', backref=db.backref('modules', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'order': self.order,
            'lessons': [l.to_dict() for l in self.lessons]
        }

class Lesson(db.Model):
    """Course lesson"""
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Markdown/HTML content (Reading/Writing)
    video_url = db.Column(db.String(500))  # Video content (Visual/Auditory)
    video_id = db.Column(db.String(50))  # YouTube ID
    duration_minutes = db.Column(db.Integer)
    order = db.Column(db.Integer, default=0)
    
    # Multi-modal VARK content
    assignment = db.Column(db.Text)  # Hands-on assignment (Kinesthetic)
    document_url = db.Column(db.String(500))  # Additional reading material (Reading/Writing)
    code_example = db.Column(db.Text)  # Code snippets (Kinesthetic)
    interactive_element = db.Column(db.Text)  # Interactive exercises (Kinesthetic)
    quiz_questions = db.Column(db.Text)  # JSON string of quiz questions (All styles)
    diagram_url = db.Column(db.String(500))  # Diagrams/infographics (Visual)
    
    # Relationships
    module = db.relationship('Module', backref=db.backref('lessons', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'content': self.content,
            'video_url': self.video_url,
            'video_id': self.video_id,
            'duration_minutes': self.duration_minutes,
            'order': self.order,
            'assignment': self.assignment,
            'document_url': self.document_url,
            'code_example': self.code_example,
            'interactive_element': self.interactive_element,
            'quiz_questions': json.loads(self.quiz_questions) if self.quiz_questions else None,
            'diagram_url': self.diagram_url
        }

class UserInteraction(db.Model):
    """User interaction tracking"""
    __tablename__ = 'user_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100))
    interaction_type = db.Column(db.String(50), nullable=False)  # CLICK, VIDEO_WATCH, QUIZ_ATTEMPT, etc.
    resource_type = db.Column(db.String(50))  # COURSE, LESSON, VIDEO, QUIZ, etc.
    resource_id = db.Column(db.Integer)
    duration = db.Column(db.Integer)  # in seconds
    interaction_metadata = db.Column(db.Text)  # JSON string (renamed from 'metadata' to avoid SQLAlchemy conflict)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'interaction_type': self.interaction_type,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'duration': self.duration,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class LearningBehavior(db.Model):
    """Aggregated learning behavior"""
    __tablename__ = 'learning_behaviors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    total_time_spent = db.Column(db.BigInteger, default=0)  # in seconds
    avg_session_duration = db.Column(db.Integer, default=0)  # in seconds
    preferred_content_type = db.Column(db.String(50))  # VIDEO, TEXT, INTERACTIVE, etc.
    engagement_score = db.Column(db.Float, default=0.0)  # 0-100
    total_sessions = db.Column(db.Integer, default=0)
    courses_completed = db.Column(db.Integer, default=0)
    courses_in_progress = db.Column(db.Integer, default=0)
    average_quiz_score = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'total_time_spent': self.total_time_spent,
            'avg_session_duration': self.avg_session_duration,
            'preferred_content_type': self.preferred_content_type,
            'engagement_score': self.engagement_score,
            'total_sessions': self.total_sessions,
            'courses_completed': self.courses_completed,
            'courses_in_progress': self.courses_in_progress,
            'average_quiz_score': self.average_quiz_score,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class LearningStyle(db.Model):
    """VARK learning style"""
    __tablename__ = 'learning_styles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    visual_score = db.Column(db.Integer, default=50)  # 0-100
    auditory_score = db.Column(db.Integer, default=50)  # 0-100
    kinesthetic_score = db.Column(db.Integer, default=50)  # 0-100
    reading_writing_score = db.Column(db.Integer, default=50)  # 0-100
    dominant_style = db.Column(db.String(50))  # VISUAL, AUDITORY, KINESTHETIC, READING_WRITING, MULTIMODAL
    confidence = db.Column(db.Float, default=0.0)  # 0-100
    data_points = db.Column(db.Integer, default=0)
    last_inferred = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'visual_score': self.visual_score,
            'auditory_score': self.auditory_score,
            'kinesthetic_score': self.kinesthetic_score,
            'reading_writing_score': self.reading_writing_score,
            'dominant_style': self.dominant_style,
            'confidence': self.confidence,
            'data_points': self.data_points,
            'last_inferred': self.last_inferred.isoformat() if self.last_inferred else None
        }

class UserConsent(db.Model):
    """Privacy consent management"""
    __tablename__ = 'user_consents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    analytics_consent = db.Column(db.Boolean, default=False)
    personalization_consent = db.Column(db.Boolean, default=False)
    data_sharing_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    data_retention_days = db.Column(db.Integer, default=365)
    consent_version = db.Column(db.String(10), default='1.0')
    consent_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'analytics_consent': self.analytics_consent,
            'personalization_consent': self.personalization_consent,
            'data_sharing_consent': self.data_sharing_consent,
            'marketing_consent': self.marketing_consent,
            'data_retention_days': self.data_retention_days,
            'consent_version': self.consent_version,
            'consent_date': self.consent_date.isoformat() if self.consent_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class CourseRecommendation(db.Model):
    """Course recommendations"""
    __tablename__ = 'course_recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    recommendation_score = db.Column(db.Float)  # 0-100
    recommendation_type = db.Column(db.String(50))  # RULE_BASED, COLLABORATIVE, CONTENT_BASED, HYBRID, AI_GENERATED
    reasoning = db.Column(db.Text)
    learning_style_match = db.Column(db.Float)  # 0-100
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    clicked = db.Column(db.Boolean, default=False)
    clicked_at = db.Column(db.DateTime)
    enrolled = db.Column(db.Boolean, default=False)
    enrolled_at = db.Column(db.DateTime)
    dismissed = db.Column(db.Boolean, default=False)
    feedback_rating = db.Column(db.Integer)  # 1-5 stars
    
    # Relationship
    course = db.relationship('Course', backref='recommendations')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'course': self.course.to_dict() if self.course else None,
            'recommendation_score': self.recommendation_score,
            'recommendation_type': self.recommendation_type,
            'reasoning': self.reasoning,
            'learning_style_match': self.learning_style_match,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'clicked': self.clicked,
            'enrolled': self.enrolled
        }

class TestResult(db.Model):
    """Test result tracking"""
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(100))
    difficulty = db.Column(db.String(50))
    score = db.Column(db.Float, nullable=False)
    correct_answers = db.Column(db.Integer)
    total_questions = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('test_results', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'topic': self.topic,
            'difficulty': self.difficulty,
            'score': self.score,
            'correct_answers': self.correct_answers,
            'total_questions': self.total_questions,
            'passed': self.passed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


# ==================== NEW LMS ENHANCEMENT MODELS ====================

class PerformanceHistory(db.Model):
    """Track detailed performance metrics for AI personalization and spaced repetition"""
    __tablename__ = 'performance_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Topic/skill tracking
    topic = db.Column(db.String(200), nullable=False)
    skill_level = db.Column(db.Float, default=50.0)  # 0-100 mastery level

    # Performance data (JSON arrays)
    quiz_scores = db.Column(db.Text)  # JSON: [{"score": 85, "date": "...", "quiz_id": 1}, ...]
    assignment_scores = db.Column(db.Text)  # JSON: [{"score": 90, "date": "...", "assignment_id": 1}, ...]

    # Learning velocity metrics
    learning_velocity = db.Column(db.Float, default=1.0)  # 0.5=slow, 1.0=normal, 2.0=fast
    avg_time_to_mastery = db.Column(db.Integer)  # Average minutes to master concepts
    total_attempts = db.Column(db.Integer, default=0)
    successful_attempts = db.Column(db.Integer, default=0)

    # Knowledge gap tracking
    weak_areas = db.Column(db.Text)  # JSON: ["subtopic1", "subtopic2"]
    strong_areas = db.Column(db.Text)  # JSON: ["subtopic1", "subtopic2"]
    misconceptions = db.Column(db.Text)  # JSON: [{"concept": "...", "incorrect_belief": "..."}]

    # Spaced repetition data (SM-2 algorithm)
    last_reviewed = db.Column(db.DateTime)
    next_review_due = db.Column(db.DateTime)
    review_interval_days = db.Column(db.Integer, default=1)
    ease_factor = db.Column(db.Float, default=2.5)  # SM-2 ease factor
    repetition_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('performance_history', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'topic': self.topic,
            'skill_level': self.skill_level,
            'quiz_scores': json.loads(self.quiz_scores) if self.quiz_scores else [],
            'assignment_scores': json.loads(self.assignment_scores) if self.assignment_scores else [],
            'learning_velocity': self.learning_velocity,
            'avg_time_to_mastery': self.avg_time_to_mastery,
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'weak_areas': json.loads(self.weak_areas) if self.weak_areas else [],
            'strong_areas': json.loads(self.strong_areas) if self.strong_areas else [],
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'next_review_due': self.next_review_due.isoformat() if self.next_review_due else None,
            'review_interval_days': self.review_interval_days,
            'ease_factor': self.ease_factor,
            'repetition_count': self.repetition_count,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LessonProgress(db.Model):
    """Granular lesson-level progress tracking"""
    __tablename__ = 'lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    # Progress status
    status = db.Column(db.String(20), default='NOT_STARTED')  # NOT_STARTED, IN_PROGRESS, COMPLETED
    completion_percentage = db.Column(db.Float, default=0.0)

    # Time tracking
    time_spent_seconds = db.Column(db.Integer, default=0)
    video_watch_percentage = db.Column(db.Float, default=0.0)

    # Content engagement flags
    content_viewed = db.Column(db.Boolean, default=False)
    video_watched = db.Column(db.Boolean, default=False)
    assignment_completed = db.Column(db.Boolean, default=False)
    quiz_attempted = db.Column(db.Boolean, default=False)
    quiz_passed = db.Column(db.Boolean, default=False)
    code_example_run = db.Column(db.Boolean, default=False)
    interactive_completed = db.Column(db.Boolean, default=False)

    # Quiz performance for this lesson
    quiz_score = db.Column(db.Float)
    quiz_attempts = db.Column(db.Integer, default=0)
    best_quiz_score = db.Column(db.Float)

    # Assignment performance
    assignment_score = db.Column(db.Float)
    assignment_submitted_at = db.Column(db.DateTime)

    # Notes and bookmarks
    user_notes = db.Column(db.Text)
    is_bookmarked = db.Column(db.Boolean, default=False)

    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('lesson_progress', lazy=True, cascade='all, delete-orphan'))
    lesson = db.relationship('Lesson', backref=db.backref('progress_records', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'lesson_id': self.lesson_id,
            'course_id': self.course_id,
            'status': self.status,
            'completion_percentage': self.completion_percentage,
            'time_spent_seconds': self.time_spent_seconds,
            'video_watch_percentage': self.video_watch_percentage,
            'content_viewed': self.content_viewed,
            'video_watched': self.video_watched,
            'assignment_completed': self.assignment_completed,
            'quiz_attempted': self.quiz_attempted,
            'quiz_passed': self.quiz_passed,
            'quiz_score': self.quiz_score,
            'quiz_attempts': self.quiz_attempts,
            'best_quiz_score': self.best_quiz_score,
            'assignment_score': self.assignment_score,
            'is_bookmarked': self.is_bookmarked,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }


class GeneratedContent(db.Model):
    """Cache AI-generated content to reduce API calls and enable offline access"""
    __tablename__ = 'generated_content'

    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(50), nullable=False)  # COURSE, QUIZ, ASSIGNMENT, LESSON, LEARNING_PATH
    content_hash = db.Column(db.String(64), unique=True, nullable=False)  # SHA-256 hash of generation params

    # Generation context
    topic = db.Column(db.String(200))
    difficulty = db.Column(db.String(20))
    learning_style = db.Column(db.String(50))
    user_level = db.Column(db.String(50))

    # Additional generation parameters (JSON)
    generation_params = db.Column(db.Text)  # JSON: {"weeks": 8, "question_count": 10, ...}

    # Generated content
    content_json = db.Column(db.Text, nullable=False)  # Full JSON content

    # Quality metrics
    quality_score = db.Column(db.Float)  # 0-100, based on user feedback
    usage_count = db.Column(db.Integer, default=0)
    positive_feedback = db.Column(db.Integer, default=0)
    negative_feedback = db.Column(db.Integer, default=0)

    # Versioning
    version = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey('generated_content.id'))  # For version history

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    access_count = db.Column(db.Integer, default=0)
    is_valid = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime)  # Optional expiration

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'content_type': self.content_type,
            'content_hash': self.content_hash,
            'topic': self.topic,
            'difficulty': self.difficulty,
            'learning_style': self.learning_style,
            'user_level': self.user_level,
            'generation_params': json.loads(self.generation_params) if self.generation_params else {},
            'content': json.loads(self.content_json) if self.content_json else {},
            'quality_score': self.quality_score,
            'usage_count': self.usage_count,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'is_valid': self.is_valid
        }


class LearningPath(db.Model):
    """Personalized learning paths for users"""
    __tablename__ = 'learning_paths'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Path metadata
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    goal = db.Column(db.Text)
    target_skill = db.Column(db.String(100))

    # Path structure (JSON)
    milestones = db.Column(db.Text)  # JSON: [{"id": 1, "title": "...", "courses": [...], "completed": false}]
    course_sequence = db.Column(db.Text)  # JSON: [course_id1, course_id2, ...]
    prerequisites = db.Column(db.Text)  # JSON: ["prerequisite1", "prerequisite2"]

    # Progress tracking
    current_milestone = db.Column(db.Integer, default=0)
    current_course_index = db.Column(db.Integer, default=0)
    overall_progress = db.Column(db.Float, default=0.0)  # 0-100
    courses_completed = db.Column(db.Integer, default=0)
    total_courses = db.Column(db.Integer, default=0)

    # Time tracking
    estimated_hours = db.Column(db.Integer)
    time_spent_hours = db.Column(db.Float, default=0.0)

    # Personalization
    adapted_for_style = db.Column(db.String(50))  # Learning style used
    difficulty_adjustment = db.Column(db.Float, default=1.0)  # Multiplier for difficulty
    pace = db.Column(db.String(20), default='NORMAL')  # SLOW, NORMAL, FAST

    # AI-generated insights
    ai_insights = db.Column(db.Text)  # JSON: AI-generated recommendations and insights

    # Status
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, PAUSED, COMPLETED, ABANDONED

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    target_completion = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationship
    user = db.relationship('User', backref=db.backref('learning_paths', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'goal': self.goal,
            'target_skill': self.target_skill,
            'milestones': json.loads(self.milestones) if self.milestones else [],
            'course_sequence': json.loads(self.course_sequence) if self.course_sequence else [],
            'current_milestone': self.current_milestone,
            'current_course_index': self.current_course_index,
            'overall_progress': self.overall_progress,
            'courses_completed': self.courses_completed,
            'total_courses': self.total_courses,
            'estimated_hours': self.estimated_hours,
            'time_spent_hours': self.time_spent_hours,
            'adapted_for_style': self.adapted_for_style,
            'difficulty_adjustment': self.difficulty_adjustment,
            'pace': self.pace,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'target_completion': self.target_completion.isoformat() if self.target_completion else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class QuizAttempt(db.Model):
    """Detailed quiz attempt tracking for adaptive learning"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    # Quiz metadata
    quiz_title = db.Column(db.String(200))
    quiz_topic = db.Column(db.String(100))
    difficulty_level = db.Column(db.String(20))  # EASY, MEDIUM, HARD

    # Performance
    score = db.Column(db.Float, nullable=False)  # Percentage
    correct_answers = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    passed = db.Column(db.Boolean)
    passing_score = db.Column(db.Float, default=70.0)

    # Time tracking
    time_taken_seconds = db.Column(db.Integer)
    time_limit_seconds = db.Column(db.Integer)

    # Detailed question performance (JSON)
    question_performance = db.Column(db.Text)  # JSON: [{"question_id": 1, "correct": true, "time_taken": 30, "concept": "..."}]
    answers_given = db.Column(db.Text)  # JSON: [{"question_id": 1, "answer": 2, "correct_answer": 1}]

    # Knowledge gap analysis
    knowledge_gaps_identified = db.Column(db.Text)  # JSON: ["concept1", "concept2"]
    concepts_mastered = db.Column(db.Text)  # JSON: ["concept1", "concept2"]

    # AI feedback
    ai_feedback = db.Column(db.Text)  # AI-generated feedback on performance
    recommended_review_topics = db.Column(db.Text)  # JSON: ["topic1", "topic2"]

    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('quiz_attempts', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'lesson_id': self.lesson_id,
            'course_id': self.course_id,
            'quiz_title': self.quiz_title,
            'quiz_topic': self.quiz_topic,
            'difficulty_level': self.difficulty_level,
            'score': self.score,
            'correct_answers': self.correct_answers,
            'total_questions': self.total_questions,
            'passed': self.passed,
            'time_taken_seconds': self.time_taken_seconds,
            'question_performance': json.loads(self.question_performance) if self.question_performance else [],
            'knowledge_gaps_identified': json.loads(self.knowledge_gaps_identified) if self.knowledge_gaps_identified else [],
            'concepts_mastered': json.loads(self.concepts_mastered) if self.concepts_mastered else [],
            'ai_feedback': self.ai_feedback,
            'recommended_review_topics': json.loads(self.recommended_review_topics) if self.recommended_review_topics else [],
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class CourseProgress(db.Model):
    """Course-level progress aggregation"""
    __tablename__ = 'course_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # Progress metrics
    status = db.Column(db.String(20), default='NOT_STARTED')  # NOT_STARTED, IN_PROGRESS, COMPLETED
    completion_percentage = db.Column(db.Float, default=0.0)

    # Lesson progress
    lessons_completed = db.Column(db.Integer, default=0)
    total_lessons = db.Column(db.Integer, default=0)
    current_lesson_id = db.Column(db.Integer)

    # Module progress
    modules_completed = db.Column(db.Integer, default=0)
    total_modules = db.Column(db.Integer, default=0)
    current_module_id = db.Column(db.Integer)

    # Quiz performance
    quizzes_attempted = db.Column(db.Integer, default=0)
    quizzes_passed = db.Column(db.Integer, default=0)
    average_quiz_score = db.Column(db.Float, default=0.0)

    # Assignment performance
    assignments_completed = db.Column(db.Integer, default=0)
    total_assignments = db.Column(db.Integer, default=0)
    average_assignment_score = db.Column(db.Float, default=0.0)

    # Time tracking
    total_time_spent_seconds = db.Column(db.Integer, default=0)
    estimated_time_remaining_seconds = db.Column(db.Integer)

    # Learning velocity for this course
    learning_velocity = db.Column(db.Float, default=1.0)

    # Timestamps
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', backref=db.backref('course_progress', lazy=True, cascade='all, delete-orphan'))
    course = db.relationship('Course', backref=db.backref('progress_records', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'status': self.status,
            'completion_percentage': self.completion_percentage,
            'lessons_completed': self.lessons_completed,
            'total_lessons': self.total_lessons,
            'modules_completed': self.modules_completed,
            'total_modules': self.total_modules,
            'quizzes_attempted': self.quizzes_attempted,
            'quizzes_passed': self.quizzes_passed,
            'average_quiz_score': self.average_quiz_score,
            'assignments_completed': self.assignments_completed,
            'total_assignments': self.total_assignments,
            'average_assignment_score': self.average_assignment_score,
            'total_time_spent_seconds': self.total_time_spent_seconds,
            'learning_velocity': self.learning_velocity,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


# ==================== PHASE 2: ADVANCED INTEGRATION MODELS ====================

class VideoEngagement(db.Model):
    """Track video engagement with VARK correlation"""
    __tablename__ = 'video_engagements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.String(50), nullable=False)  # YouTube video ID
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    # Engagement metrics
    watch_duration_seconds = db.Column(db.Integer, default=0)
    total_video_duration = db.Column(db.Integer)
    watch_percentage = db.Column(db.Float, default=0.0)
    replay_count = db.Column(db.Integer, default=0)
    pause_count = db.Column(db.Integer, default=0)
    seek_forward_count = db.Column(db.Integer, default=0)
    seek_backward_count = db.Column(db.Integer, default=0)
    playback_speed = db.Column(db.Float, default=1.0)

    # VARK correlation at time of viewing
    user_vark_style = db.Column(db.String(50))  # Dominant style when watched
    visual_score_at_view = db.Column(db.Integer)
    auditory_score_at_view = db.Column(db.Integer)

    # Video characteristics
    video_type = db.Column(db.String(50))  # tutorial, lecture, demo, etc.
    video_title = db.Column(db.String(500))
    video_channel = db.Column(db.String(200))
    has_captions = db.Column(db.Boolean, default=False)
    vark_suitability = db.Column(db.Text)  # JSON: {"visual": 80, "auditory": 60, ...}

    # Engagement quality
    engagement_score = db.Column(db.Float)  # 0-100 based on watch patterns
    completed = db.Column(db.Boolean, default=False)

    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('video_engagements', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_id': self.video_id,
            'lesson_id': self.lesson_id,
            'watch_duration_seconds': self.watch_duration_seconds,
            'total_video_duration': self.total_video_duration,
            'watch_percentage': self.watch_percentage,
            'replay_count': self.replay_count,
            'pause_count': self.pause_count,
            'playback_speed': self.playback_speed,
            'user_vark_style': self.user_vark_style,
            'video_type': self.video_type,
            'video_title': self.video_title,
            'has_captions': self.has_captions,
            'vark_suitability': json.loads(self.vark_suitability) if self.vark_suitability else {},
            'engagement_score': self.engagement_score,
            'completed': self.completed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class UserCourseSequence(db.Model):
    """Track course completion sequences for sequence-aware recommendations"""
    __tablename__ = 'user_course_sequences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    sequence_position = db.Column(db.Integer)  # Order in user's learning journey

    # Context at completion
    difficulty_at_completion = db.Column(db.String(20))
    skill_level_at_completion = db.Column(db.Float)
    duration_days = db.Column(db.Integer)  # Days to complete

    # Performance
    final_quiz_score = db.Column(db.Float)
    engagement_score = db.Column(db.Float)

    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('course_sequences', lazy=True, cascade='all, delete-orphan'))
    course = db.relationship('Course', backref=db.backref('completion_sequences', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'sequence_position': self.sequence_position,
            'difficulty_at_completion': self.difficulty_at_completion,
            'skill_level_at_completion': self.skill_level_at_completion,
            'duration_days': self.duration_days,
            'final_quiz_score': self.final_quiz_score,
            'engagement_score': self.engagement_score,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class LatentFactors(db.Model):
    """Store pre-computed matrix factorization latent factors"""
    __tablename__ = 'latent_factors'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False)  # 'USER' or 'COURSE'
    entity_id = db.Column(db.Integer, nullable=False)

    # Latent factor vectors (stored as JSON)
    factors = db.Column(db.Text, nullable=False)  # JSON array of floats
    num_factors = db.Column(db.Integer, default=50)

    # Model metadata
    model_version = db.Column(db.String(50))
    computed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('entity_type', 'entity_id', 'model_version', name='uq_latent_factor'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'factors': json.loads(self.factors) if self.factors else [],
            'num_factors': self.num_factors,
            'model_version': self.model_version,
            'computed_at': self.computed_at.isoformat() if self.computed_at else None
        }


class LearningSession(db.Model):
    """Track learning sessions for behavioral analysis"""
    __tablename__ = 'learning_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)

    # Session timing
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)

    # Device context
    device_type = db.Column(db.String(50))  # mobile, desktop, tablet
    browser = db.Column(db.String(50))
    platform = db.Column(db.String(50))

    # Activity summary
    interactions_count = db.Column(db.Integer, default=0)
    videos_watched = db.Column(db.Integer, default=0)
    documents_read = db.Column(db.Integer, default=0)
    quizzes_attempted = db.Column(db.Integer, default=0)
    assignments_worked = db.Column(db.Integer, default=0)

    # VARK indicators for this session
    session_vark_scores = db.Column(db.Text)  # JSON: {visual: n, auditory: n, ...}

    # Engagement quality
    focus_score = db.Column(db.Float)  # 0-100, based on activity patterns
    distraction_events = db.Column(db.Integer, default=0)  # Tab switches, long pauses
    active_time_ratio = db.Column(db.Float)  # Active vs idle time

    # Learning outcomes
    lessons_completed = db.Column(db.Integer, default=0)
    quiz_scores = db.Column(db.Text)  # JSON array of scores

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('learning_sessions', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.duration_seconds,
            'device_type': self.device_type,
            'interactions_count': self.interactions_count,
            'videos_watched': self.videos_watched,
            'quizzes_attempted': self.quizzes_attempted,
            'session_vark_scores': json.loads(self.session_vark_scores) if self.session_vark_scores else {},
            'focus_score': self.focus_score,
            'lessons_completed': self.lessons_completed
        }


class VARKPrediction(db.Model):
    """Store VARK predictions with confidence intervals"""
    __tablename__ = 'vark_predictions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Current prediction
    predicted_style = db.Column(db.String(50))
    prediction_confidence = db.Column(db.Float)

    # Score distributions (for nuanced multimodal users)
    visual_mean = db.Column(db.Float)
    visual_std = db.Column(db.Float)
    auditory_mean = db.Column(db.Float)
    auditory_std = db.Column(db.Float)
    kinesthetic_mean = db.Column(db.Float)
    kinesthetic_std = db.Column(db.Float)
    reading_writing_mean = db.Column(db.Float)
    reading_writing_std = db.Column(db.Float)

    # Probability distribution
    probability_distribution = db.Column(db.Text)  # JSON: {"VISUAL": 0.45, "AUDITORY": 0.25, ...}

    # Prediction metadata
    model_version = db.Column(db.String(50))
    data_points_used = db.Column(db.Integer)
    sessions_analyzed = db.Column(db.Integer)

    # Temporal stability
    style_stability = db.Column(db.Float)  # How consistent over time (0-1)
    last_change_date = db.Column(db.DateTime)
    style_history = db.Column(db.Text)  # JSON: [{"date": "...", "style": "VISUAL"}, ...]

    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('vark_prediction', uselist=False, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'predicted_style': self.predicted_style,
            'prediction_confidence': self.prediction_confidence,
            'visual_mean': self.visual_mean,
            'visual_std': self.visual_std,
            'auditory_mean': self.auditory_mean,
            'auditory_std': self.auditory_std,
            'kinesthetic_mean': self.kinesthetic_mean,
            'kinesthetic_std': self.kinesthetic_std,
            'reading_writing_mean': self.reading_writing_mean,
            'reading_writing_std': self.reading_writing_std,
            'probability_distribution': json.loads(self.probability_distribution) if self.probability_distribution else {},
            'style_stability': self.style_stability,
            'data_points_used': self.data_points_used,
            'sessions_analyzed': self.sessions_analyzed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EngagementEvent(db.Model):
    """Fine-grained engagement events for behavioral analysis"""
    __tablename__ = 'engagement_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100))

    # Event details
    event_type = db.Column(db.String(50), nullable=False)  # scroll, click, pause, seek, highlight, etc.
    resource_type = db.Column(db.String(50))  # VIDEO, DOCUMENT, CODE, QUIZ
    resource_id = db.Column(db.Integer)

    # Event context
    event_data = db.Column(db.Text)  # JSON with event-specific data
    position = db.Column(db.Float)  # Position in video/document (0-100%)

    # Timing
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration_ms = db.Column(db.Integer)  # How long the event lasted

    # Derived metrics
    engagement_signal = db.Column(db.Float)  # Positive/negative engagement indicator (-1 to 1)
    vark_signal = db.Column(db.Text)  # JSON: {"visual": 2, "auditory": 0, ...}

    # Relationships
    user = db.relationship('User', backref=db.backref('engagement_events', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'event_data': json.loads(self.event_data) if self.event_data else {},
            'position': self.position,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration_ms': self.duration_ms,
            'engagement_signal': self.engagement_signal,
            'vark_signal': json.loads(self.vark_signal) if self.vark_signal else {}
        }


class ConceptMastery(db.Model):
    """Track mastery of individual concepts within topics"""
    __tablename__ = 'concept_mastery'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    concept_name = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200))  # Parent topic
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    # Mastery metrics
    mastery_level = db.Column(db.Float, default=0.0)  # 0-100
    confidence = db.Column(db.Float, default=0.0)  # 0-100, how confident the system is
    attempts = db.Column(db.Integer, default=0)
    correct_attempts = db.Column(db.Integer, default=0)

    # Performance tracking
    first_exposure = db.Column(db.DateTime)
    last_practiced = db.Column(db.DateTime)
    time_to_mastery_minutes = db.Column(db.Integer)  # Time from first exposure to mastery
    total_practice_time_seconds = db.Column(db.Integer, default=0)

    # Learning pattern
    learning_curve = db.Column(db.Text)  # JSON: [{"date": "...", "score": 80}, ...]
    difficulty_rating = db.Column(db.Float)  # How difficult this concept is for user (0-100)

    # Related concepts
    prerequisites = db.Column(db.Text)  # JSON: ["concept1", "concept2"]
    related_concepts = db.Column(db.Text)  # JSON: ["concept1", "concept2"]

    # Misconceptions tracking
    misconceptions = db.Column(db.Text)  # JSON: [{"incorrect": "...", "correct": "...", "count": 3}]

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('concept_masteries', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'concept_name', 'topic', name='uq_user_concept_topic'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'concept_name': self.concept_name,
            'topic': self.topic,
            'course_id': self.course_id,
            'mastery_level': self.mastery_level,
            'confidence': self.confidence,
            'attempts': self.attempts,
            'correct_attempts': self.correct_attempts,
            'accuracy': (self.correct_attempts / self.attempts * 100) if self.attempts > 0 else 0,
            'first_exposure': self.first_exposure.isoformat() if self.first_exposure else None,
            'last_practiced': self.last_practiced.isoformat() if self.last_practiced else None,
            'time_to_mastery_minutes': self.time_to_mastery_minutes,
            'difficulty_rating': self.difficulty_rating,
            'learning_curve': json.loads(self.learning_curve) if self.learning_curve else [],
            'prerequisites': json.loads(self.prerequisites) if self.prerequisites else [],
            'misconceptions': json.loads(self.misconceptions) if self.misconceptions else []
        }


class SessionSummary(db.Model):
    """Comprehensive learning session summaries"""
    __tablename__ = 'session_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)

    # Session timing
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Float)

    # Learning outcomes
    concepts_learned = db.Column(db.Text)  # JSON: ["concept1", "concept2"]
    concepts_reinforced = db.Column(db.Text)  # JSON
    concepts_struggled = db.Column(db.Text)  # JSON

    # Progress metrics
    lessons_completed = db.Column(db.Integer, default=0)
    quizzes_taken = db.Column(db.Integer, default=0)
    quiz_avg_score = db.Column(db.Float)
    assignments_submitted = db.Column(db.Integer, default=0)
    videos_watched = db.Column(db.Integer, default=0)
    video_completion_rate = db.Column(db.Float)

    # VARK analysis
    session_vark_profile = db.Column(db.Text)  # JSON: {"visual": 40, "auditory": 30, ...}
    dominant_learning_mode = db.Column(db.String(50))
    vark_confidence = db.Column(db.Float)

    # Engagement metrics
    engagement_score = db.Column(db.Float)  # 0-100
    focus_score = db.Column(db.Float)  # 0-100
    productivity_score = db.Column(db.Float)  # 0-100 based on outcomes vs time

    # AI-generated insights
    session_insights = db.Column(db.Text)  # JSON: AI-generated observations
    recommendations = db.Column(db.Text)  # JSON: What to do next

    # Comparison metrics
    compared_to_avg_duration = db.Column(db.Float)  # % difference from user's avg
    compared_to_avg_productivity = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('session_summaries', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_minutes': self.duration_minutes,
            'concepts_learned': json.loads(self.concepts_learned) if self.concepts_learned else [],
            'concepts_reinforced': json.loads(self.concepts_reinforced) if self.concepts_reinforced else [],
            'concepts_struggled': json.loads(self.concepts_struggled) if self.concepts_struggled else [],
            'lessons_completed': self.lessons_completed,
            'quizzes_taken': self.quizzes_taken,
            'quiz_avg_score': self.quiz_avg_score,
            'videos_watched': self.videos_watched,
            'session_vark_profile': json.loads(self.session_vark_profile) if self.session_vark_profile else {},
            'dominant_learning_mode': self.dominant_learning_mode,
            'engagement_score': self.engagement_score,
            'focus_score': self.focus_score,
            'productivity_score': self.productivity_score,
            'session_insights': json.loads(self.session_insights) if self.session_insights else [],
            'recommendations': json.loads(self.recommendations) if self.recommendations else []
        }


class ContentBias(db.Model):
    """Track content exposure and bias metrics"""
    __tablename__ = 'content_bias'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Content type distribution
    video_exposure_pct = db.Column(db.Float, default=0.0)
    document_exposure_pct = db.Column(db.Float, default=0.0)
    interactive_exposure_pct = db.Column(db.Float, default=0.0)
    quiz_exposure_pct = db.Column(db.Float, default=0.0)

    # Difficulty distribution
    beginner_content_pct = db.Column(db.Float, default=0.0)
    intermediate_content_pct = db.Column(db.Float, default=0.0)
    advanced_content_pct = db.Column(db.Float, default=0.0)

    # Topic diversity
    topic_distribution = db.Column(db.Text)  # JSON: {"python": 40, "javascript": 30, ...}
    topic_diversity_score = db.Column(db.Float)  # 0-100, higher = more diverse

    # Instructor/source diversity
    source_distribution = db.Column(db.Text)  # JSON
    source_diversity_score = db.Column(db.Float)

    # Bias indicators
    vark_content_alignment = db.Column(db.Float)  # How well content matches VARK
    difficulty_appropriateness = db.Column(db.Float)  # How well difficulty matches skill

    # Recommendations to balance
    underexposed_types = db.Column(db.Text)  # JSON: ["document", "quiz"]
    underexposed_topics = db.Column(db.Text)  # JSON

    last_calculated = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('content_bias', uselist=False, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_exposure_pct': self.video_exposure_pct,
            'document_exposure_pct': self.document_exposure_pct,
            'interactive_exposure_pct': self.interactive_exposure_pct,
            'quiz_exposure_pct': self.quiz_exposure_pct,
            'beginner_content_pct': self.beginner_content_pct,
            'intermediate_content_pct': self.intermediate_content_pct,
            'advanced_content_pct': self.advanced_content_pct,
            'topic_distribution': json.loads(self.topic_distribution) if self.topic_distribution else {},
            'topic_diversity_score': self.topic_diversity_score,
            'vark_content_alignment': self.vark_content_alignment,
            'difficulty_appropriateness': self.difficulty_appropriateness,
            'underexposed_types': json.loads(self.underexposed_types) if self.underexposed_types else [],
            'underexposed_topics': json.loads(self.underexposed_topics) if self.underexposed_topics else []
        }
