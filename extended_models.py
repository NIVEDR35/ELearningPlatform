# Extended models for complete course structure with modules, lessons, quizzes, and assignments

from models import db
from datetime import datetime

class CourseModule(db.Model):
    """Course modules/sections"""
    __tablename__ = 'course_modules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    duration_hours = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    lessons = db.relationship('Lesson', backref='module', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'order_index': self.order_index,
            'duration_hours': self.duration_hours,
            'lessons_count': len(self.lessons) if self.lessons else 0
        }

class Lesson(db.Model):
    """Individual lessons within modules"""
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('course_modules.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Markdown or HTML content
    content_type = db.Column(db.String(50))  # VIDEO, TEXT, INTERACTIVE, QUIZ
    video_url = db.Column(db.String(500))  # YouTube URL
    video_id = db.Column(db.String(50))  # YouTube video ID
    duration_minutes = db.Column(db.Integer)
    order_index = db.Column(db.Integer, default=0)
    is_free = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'content': self.content,
            'content_type': self.content_type,
            'video_url': self.video_url,
            'video_id': self.video_id,
            'duration_minutes': self.duration_minutes,
            'order_index': self.order_index,
            'is_free': self.is_free
        }

class Quiz(db.Model):
    """Quizzes for courses/modules"""
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('course_modules.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit_minutes = db.Column(db.Integer)  # 0 = no limit
    passing_score = db.Column(db.Integer, default=70)  # Percentage
    max_attempts = db.Column(db.Integer, default=3)
    is_adaptive = db.Column(db.Boolean, default=False)  # AI-powered adaptive quiz
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'module_id': self.module_id,
            'title': self.title,
            'description': self.description,
            'time_limit_minutes': self.time_limit_minutes,
            'passing_score': self.passing_score,
            'max_attempts': self.max_attempts,
            'is_adaptive': self.is_adaptive,
            'questions_count': len(self.questions) if self.questions else 0
        }

class QuizQuestion(db.Model):
    """Questions in a quiz"""
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50))  # MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER
    options = db.Column(db.Text)  # JSON array of options
    correct_answer = db.Column(db.Text)  # JSON for multiple correct answers
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    difficulty = db.Column(db.String(20))  # EASY, MEDIUM, HARD
    order_index = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': json.loads(self.options) if self.options else [],
            'explanation': self.explanation,
            'points': self.points,
            'difficulty': self.difficulty,
            'order_index': self.order_index
        }

class QuizAttempt(db.Model):
    """User quiz attempts"""
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Float)  # Percentage
    answers = db.Column(db.Text)  # JSON of user answers
    time_taken_minutes = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'user_id': self.user_id,
            'score': self.score,
            'answers': json.loads(self.answers) if self.answers else {},
            'time_taken_minutes': self.time_taken_minutes,
            'passed': self.passed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class Assignment(db.Model):
    """Course assignments"""
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('course_modules.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    max_points = db.Column(db.Integer, default=100)
    submission_type = db.Column(db.String(50))  # FILE, TEXT, CODE, URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'module_id': self.module_id,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'max_points': self.max_points,
            'submission_type': self.submission_type
        }

class AssignmentSubmission(db.Model):
    """User assignment submissions"""
    __tablename__ = 'assignment_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_text = db.Column(db.Text)
    submission_url = db.Column(db.String(500))
    file_path = db.Column(db.String(500))
    score = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    status = db.Column(db.String(50))  # SUBMITTED, GRADED, RETURNED
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'user_id': self.user_id,
            'submission_text': self.submission_text,
            'submission_url': self.submission_url,
            'score': self.score,
            'feedback': self.feedback,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None
        }

class UserProgress(db.Model):
    """Track user progress through courses"""
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('course_modules.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    completed = db.Column(db.Boolean, default=False)
    progress_percentage = db.Column(db.Float, default=0.0)
    time_spent_minutes = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'course_id': self.course_id,
            'module_id': self.module_id,
            'lesson_id': self.lesson_id,
            'completed': self.completed,
            'progress_percentage': self.progress_percentage,
            'time_spent_minutes': self.time_spent_minutes,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
