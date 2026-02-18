import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///adaptive_learning.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Gemini AI Configuration
    GEMINI_API_KEY = 'AIzaSyCl1zPkJHkPT8MIZAuUafCn-30Gt-fISaE'
    GEMINI_PROJECT_ID = 'projects/83810955718'
    GEMINI_PROJECT_NUMBER = '83810955718'
    GEMINI_MODEL = 'gemini-2.0-flash'  # Stable 2.0 model
    
    # Analytics Configuration
    MIN_DATA_POINTS_FOR_INFERENCE = 20
    CONFIDENCE_THRESHOLD = 50.0
    ENGAGEMENT_WINDOW_DAYS = 30
    
    # Privacy Configuration
    DEFAULT_DATA_RETENTION_DAYS = 365
    CONSENT_VERSION = '1.0'
    ENABLE_DIFFERENTIAL_PRIVACY = True
    PRIVACY_EPSILON = 0.1  # Differential privacy parameter
    
    # Recommendation Configuration
    COLD_START_THRESHOLD = 5  # Number of interactions before ML kicks in
    RECOMMENDATION_COUNT = 10
    SIMILARITY_THRESHOLD = 0.3

    # ==================== LMS ENHANCEMENT CONFIGURATION ====================

    # AI Content Generation
    AI_CACHE_ENABLED = True
    AI_CACHE_VALIDITY_DAYS = 30
    MAX_AI_RETRIES = 3
    AI_REQUEST_TIMEOUT = 30  # seconds

    # Progress Tracking
    MIN_INTERACTIONS_FOR_VELOCITY = 5
    VELOCITY_CALCULATION_WINDOW_DAYS = 30
    LESSON_COMPLETION_VIDEO_THRESHOLD = 90  # % of video to count as watched

    # Knowledge Gap Analysis
    KNOWLEDGE_GAP_THRESHOLD = 0.6  # Below this accuracy = weak area
    MASTERY_THRESHOLD = 0.8  # Above this accuracy = strong area
    MIN_QUESTIONS_FOR_GAP_ANALYSIS = 3

    # Spaced Repetition (SM-2 Algorithm)
    SR_MIN_INTERVAL_DAYS = 1
    SR_MAX_INTERVAL_DAYS = 365
    SR_DEFAULT_EASE_FACTOR = 2.5
    SR_MIN_EASE_FACTOR = 1.3

    # Personalization
    DIFFICULTY_ADJUSTMENT_THRESHOLD_HIGH = 85  # Score above this = increase difficulty
    DIFFICULTY_ADJUSTMENT_THRESHOLD_LOW = 60  # Score below this = decrease difficulty
    DEFAULT_SESSION_DURATION_MINUTES = 30

    # Learning Path
    DEFAULT_LEARNING_PATH_WEEKS = 12
    MAX_MILESTONES_PER_PATH = 10

    # Content Generation Limits
    MAX_MODULES_PER_COURSE = 10
    MAX_LESSONS_PER_MODULE = 5
    MAX_QUIZ_QUESTIONS = 20
    DEFAULT_QUIZ_QUESTIONS = 10
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS Configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000']
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'mp4', 'mp3'}

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Override with production database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/adaptive_learning'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
