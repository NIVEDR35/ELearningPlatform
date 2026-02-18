"""
Personalization Service
Manages personalized learning based on user performance:
- User learning profile compilation
- Difficulty adjustment based on performance
- Spaced repetition scheduling (SM-2 algorithm)
- Content adaptation for learning styles
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

from models import (
    db, User, LearningStyle, LearningBehavior, PerformanceHistory,
    LessonProgress, CourseProgress, QuizAttempt, Course
)
from progress_tracking_service import get_progress_service
from ai_content_service import get_ai_content_service


class PersonalizationService:
    """Manage personalized learning based on performance"""

    # Difficulty levels in order
    DIFFICULTY_LEVELS = ['BEGINNER', 'EASY', 'INTERMEDIATE', 'ADVANCED', 'EXPERT']

    # Spaced repetition parameters (SM-2 algorithm)
    SR_MIN_EASE_FACTOR = 1.3
    SR_DEFAULT_EASE_FACTOR = 2.5
    SR_MIN_INTERVAL = 1  # days
    SR_MAX_INTERVAL = 365  # days

    def __init__(self):
        self.progress_service = get_progress_service()
        self.ai_service = None  # Lazy load to avoid circular imports

    def _get_ai_service(self):
        """Lazy load AI service"""
        if self.ai_service is None:
            self.ai_service = get_ai_content_service()
        return self.ai_service

    # ==================== USER LEARNING PROFILE ====================

    def get_user_learning_profile(self, user_id: int) -> Dict:
        """
        Build comprehensive learning profile for personalization.

        Args:
            user_id: User ID

        Returns:
            Complete learning profile dict
        """
        # Get learning style
        style = LearningStyle.query.filter_by(user_id=user_id).first()

        # Get learning behavior
        behavior = LearningBehavior.query.filter_by(user_id=user_id).first()

        # Calculate velocity
        velocity = self.progress_service.calculate_learning_velocity(user_id)

        # Get knowledge gaps
        gaps = self.progress_service.identify_knowledge_gaps(user_id)

        # Get overall skill level
        skill_level = self._calculate_overall_skill_level(user_id)

        # Get preferred session duration
        preferred_duration = self._get_preferred_session_duration(user_id)

        # Get completion rate
        completion_rate = self._calculate_completion_rate(user_id)

        return {
            'user_id': user_id,
            # Learning style (VARK)
            'learning_style': style.dominant_style if style else 'MULTIMODAL',
            'visual': style.visual_score if style else 50,
            'auditory': style.auditory_score if style else 50,
            'kinesthetic': style.kinesthetic_score if style else 50,
            'reading_writing': style.reading_writing_score if style else 50,
            'style_confidence': style.confidence if style else 0,
            'style_data_points': style.data_points if style else 0,

            # Skill and performance
            'skill_level': skill_level,
            'avg_quiz_score': behavior.average_quiz_score if behavior else 0,
            'completion_rate': completion_rate,

            # Learning velocity
            'learning_velocity': velocity.get('velocity', 1.0),
            'velocity_classification': velocity.get('classification', 'NORMAL'),

            # Engagement
            'engagement_score': behavior.engagement_score if behavior else 50,
            'total_time_spent_hours': (behavior.total_time_spent or 0) / 3600 if behavior else 0,
            'courses_completed': behavior.courses_completed if behavior else 0,

            # Knowledge state
            'weak_areas': [w['topic'] for w in gaps.get('weak_areas', [])],
            'strong_areas': [s['topic'] for s in gaps.get('strong_areas', [])],

            # Preferences
            'preferred_duration': preferred_duration,
            'preferred_content_type': behavior.preferred_content_type if behavior else 'MIXED'
        }

    def _calculate_overall_skill_level(self, user_id: int) -> float:
        """Calculate overall skill level (0-100)"""
        # Get all performance history
        performances = PerformanceHistory.query.filter_by(user_id=user_id).all()

        if not performances:
            # No history - use quiz scores if available
            behavior = LearningBehavior.query.filter_by(user_id=user_id).first()
            if behavior and behavior.average_quiz_score:
                return behavior.average_quiz_score
            return 50.0  # Default middle level

        # Average skill level across topics
        total_skill = sum(p.skill_level for p in performances)
        return total_skill / len(performances)

    def _get_preferred_session_duration(self, user_id: int) -> int:
        """Determine preferred session duration based on behavior"""
        # Analyze session durations from interactions
        from models import UserInteraction

        # Get average session duration
        behavior = LearningBehavior.query.filter_by(user_id=user_id).first()

        if behavior and behavior.avg_session_duration:
            avg_duration = behavior.avg_session_duration / 60  # Convert to minutes

            # Round to standard durations
            if avg_duration <= 15:
                return 15
            elif avg_duration <= 30:
                return 30
            elif avg_duration <= 45:
                return 45
            elif avg_duration <= 60:
                return 60
            else:
                return 90

        return 30  # Default 30 minutes

    def _calculate_completion_rate(self, user_id: int) -> float:
        """Calculate course/lesson completion rate"""
        # Get course progress
        progress_records = CourseProgress.query.filter_by(user_id=user_id).all()

        if not progress_records:
            return 0.0

        total_completion = sum(p.completion_percentage for p in progress_records)
        return total_completion / len(progress_records)

    # ==================== PERFORMANCE HISTORY ====================

    def get_performance_history_dict(self, user_id: int) -> Dict:
        """Get performance history as dict for AI prompts"""
        profile = self.get_user_learning_profile(user_id)

        # Get recent quiz attempts
        recent_quizzes = QuizAttempt.query.filter_by(
            user_id=user_id
        ).order_by(
            QuizAttempt.completed_at.desc()
        ).limit(10).all()

        recent_scores = [q.score for q in recent_quizzes if q.score is not None]

        return {
            'avg_quiz_score': profile['avg_quiz_score'],
            'recent_avg_score': sum(recent_scores) / len(recent_scores) if recent_scores else 0,
            'weak_areas': profile['weak_areas'],
            'strong_areas': profile['strong_areas'],
            'completion_rate': profile['completion_rate'],
            'learning_velocity': profile['learning_velocity'],
            'total_quizzes_taken': len(recent_quizzes),
            'skill_level': profile['skill_level']
        }

    def update_performance_history(
        self,
        user_id: int,
        topic: str,
        score: float,
        is_quiz: bool = True,
        concepts_correct: List[str] = None,
        concepts_wrong: List[str] = None
    ) -> Dict:
        """
        Update performance history after quiz/assignment completion.

        Args:
            user_id: User ID
            topic: Topic/skill area
            score: Score achieved (0-100)
            is_quiz: True if quiz, False if assignment
            concepts_correct: List of correctly answered concepts
            concepts_wrong: List of incorrectly answered concepts

        Returns:
            Updated performance history
        """
        # Get or create performance history
        perf = PerformanceHistory.query.filter_by(
            user_id=user_id,
            topic=topic
        ).first()

        if not perf:
            perf = PerformanceHistory(
                user_id=user_id,
                topic=topic
            )
            db.session.add(perf)

        # Update scores
        if is_quiz:
            scores = json.loads(perf.quiz_scores) if perf.quiz_scores else []
            scores.append({
                'score': score,
                'date': datetime.utcnow().isoformat()
            })
            # Keep last 20 scores
            perf.quiz_scores = json.dumps(scores[-20:])
        else:
            scores = json.loads(perf.assignment_scores) if perf.assignment_scores else []
            scores.append({
                'score': score,
                'date': datetime.utcnow().isoformat()
            })
            perf.assignment_scores = json.dumps(scores[-20:])

        # Update attempt counts
        perf.total_attempts = (perf.total_attempts or 0) + 1
        if score >= 70:
            perf.successful_attempts = (perf.successful_attempts or 0) + 1

        # Update skill level (weighted moving average)
        old_skill = perf.skill_level or 50
        # Weight recent performance more heavily
        weight = min(0.3, 1.0 / (perf.total_attempts + 1))
        perf.skill_level = old_skill * (1 - weight) + score * weight

        # Update weak/strong areas based on concepts
        if concepts_wrong:
            weak = json.loads(perf.weak_areas) if perf.weak_areas else []
            for concept in concepts_wrong:
                if concept not in weak:
                    weak.append(concept)
            perf.weak_areas = json.dumps(weak[-10:])  # Keep last 10

        if concepts_correct:
            strong = json.loads(perf.strong_areas) if perf.strong_areas else []
            # Remove from weak if now correct
            weak = json.loads(perf.weak_areas) if perf.weak_areas else []
            for concept in concepts_correct:
                if concept in weak:
                    weak.remove(concept)
                if concept not in strong:
                    strong.append(concept)
            perf.weak_areas = json.dumps(weak)
            perf.strong_areas = json.dumps(strong[-10:])

        # Update spaced repetition
        perf = self._update_spaced_repetition(perf, score)

        db.session.commit()

        return perf.to_dict()

    # ==================== SPACED REPETITION (SM-2) ====================

    def _update_spaced_repetition(self, perf: PerformanceHistory, score: float) -> PerformanceHistory:
        """
        Update spaced repetition schedule using SM-2 algorithm.

        SM-2 Algorithm:
        - Quality of response (q): 0-5 scale based on score
        - Ease Factor (EF): How easy the material is (min 1.3)
        - Interval: Days until next review
        """
        # Convert score (0-100) to quality (0-5)
        quality = self._score_to_quality(score)

        # Get current ease factor
        ef = perf.ease_factor or self.SR_DEFAULT_EASE_FACTOR

        # Update ease factor
        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ef = max(self.SR_MIN_EASE_FACTOR, ef)
        perf.ease_factor = ef

        # Calculate next interval
        rep_count = perf.repetition_count or 0

        if quality < 3:
            # Failed - reset
            perf.review_interval_days = self.SR_MIN_INTERVAL
            perf.repetition_count = 0
        else:
            # Passed - increase interval
            if rep_count == 0:
                interval = 1
            elif rep_count == 1:
                interval = 6
            else:
                current_interval = perf.review_interval_days or 1
                interval = int(current_interval * ef)

            interval = min(interval, self.SR_MAX_INTERVAL)
            perf.review_interval_days = interval
            perf.repetition_count = rep_count + 1

        # Set review dates
        perf.last_reviewed = datetime.utcnow()
        perf.next_review_due = datetime.utcnow() + timedelta(days=perf.review_interval_days)

        return perf

    def _score_to_quality(self, score: float) -> int:
        """Convert percentage score to SM-2 quality (0-5)"""
        if score >= 95:
            return 5  # Perfect
        elif score >= 85:
            return 4  # Correct with hesitation
        elif score >= 70:
            return 3  # Correct with difficulty
        elif score >= 50:
            return 2  # Incorrect but close
        elif score >= 25:
            return 1  # Incorrect
        else:
            return 0  # Complete blackout

    def get_review_schedule(self, user_id: int) -> Dict:
        """
        Get spaced repetition review schedule.

        Returns:
            Schedule of topics due for review
        """
        now = datetime.utcnow()

        # Get all performance history
        all_topics = PerformanceHistory.query.filter_by(user_id=user_id).all()

        due_now = []
        upcoming = []
        mastered = []

        for perf in all_topics:
            topic_info = {
                'topic': perf.topic,
                'skill_level': perf.skill_level,
                'last_reviewed': perf.last_reviewed.isoformat() if perf.last_reviewed else None,
                'next_review': perf.next_review_due.isoformat() if perf.next_review_due else None,
                'interval_days': perf.review_interval_days,
                'repetition_count': perf.repetition_count
            }

            if perf.next_review_due:
                if perf.next_review_due <= now:
                    due_now.append(topic_info)
                elif perf.next_review_due <= now + timedelta(days=7):
                    upcoming.append(topic_info)

            # Check if mastered (high skill, long interval)
            if perf.skill_level >= 85 and (perf.review_interval_days or 0) >= 30:
                mastered.append(topic_info)

        # Sort by urgency
        due_now.sort(key=lambda x: x['next_review'] or '')

        return {
            'due_now': due_now,
            'due_this_week': upcoming,
            'mastered_topics': mastered,
            'total_topics': len(all_topics),
            'topics_due_count': len(due_now)
        }

    def generate_review_content(self, user_id: int, topic: str) -> Dict:
        """Generate review content for a topic"""
        ai_service = self._get_ai_service()

        # Get performance for this topic
        perf = PerformanceHistory.query.filter_by(
            user_id=user_id,
            topic=topic
        ).first()

        user_profile = self.get_user_learning_profile(user_id)

        # Generate focused review quiz
        user_performance = {
            'recent_avg_score': perf.skill_level if perf else 50,
            'weak_areas': json.loads(perf.weak_areas) if perf and perf.weak_areas else [],
            'strong_areas': json.loads(perf.strong_areas) if perf and perf.strong_areas else []
        }

        quiz = ai_service.generate_adaptive_quiz(
            topic=topic,
            user_performance=user_performance,
            learning_style=user_profile['learning_style'],
            question_count=5  # Short review quiz
        )

        return {
            'topic': topic,
            'review_type': 'SPACED_REPETITION',
            'current_skill_level': perf.skill_level if perf else 50,
            'repetition_count': perf.repetition_count if perf else 0,
            'quiz': quiz
        }

    # ==================== DIFFICULTY ADJUSTMENT ====================

    def adjust_difficulty_for_user(self, user_id: int, base_difficulty: str) -> str:
        """
        Adjust content difficulty based on user performance.

        Args:
            user_id: User ID
            base_difficulty: Base difficulty level

        Returns:
            Adjusted difficulty level
        """
        profile = self.get_user_learning_profile(user_id)

        try:
            base_index = self.DIFFICULTY_LEVELS.index(base_difficulty.upper())
        except ValueError:
            base_index = 2  # Default to INTERMEDIATE

        adjusted_index = base_index

        # Adjust based on quiz performance
        avg_score = profile['avg_quiz_score']
        if avg_score >= 85:
            # High performer - increase difficulty
            adjusted_index = min(base_index + 1, len(self.DIFFICULTY_LEVELS) - 1)
        elif avg_score < 60:
            # Struggling - decrease difficulty
            adjusted_index = max(base_index - 1, 0)

        # Adjust based on completion rate
        completion_rate = profile['completion_rate']
        if completion_rate < 50 and adjusted_index > 0:
            # Low completion - might be too hard
            adjusted_index -= 1

        # Adjust based on learning velocity
        velocity = profile['velocity_classification']
        if velocity == 'FAST' and adjusted_index < len(self.DIFFICULTY_LEVELS) - 1:
            adjusted_index += 1
        elif velocity == 'SLOW' and adjusted_index > 0:
            adjusted_index -= 1

        return self.DIFFICULTY_LEVELS[adjusted_index]

    def get_recommended_difficulty(self, user_id: int, topic: str = None) -> Dict:
        """
        Get recommended difficulty with explanation.

        Args:
            user_id: User ID
            topic: Optional specific topic

        Returns:
            Recommended difficulty with reasoning
        """
        profile = self.get_user_learning_profile(user_id)

        # Base recommendation on skill level
        skill = profile['skill_level']
        if skill >= 80:
            recommended = 'ADVANCED'
            reason = "Your high skill level suggests you're ready for advanced content."
        elif skill >= 60:
            recommended = 'INTERMEDIATE'
            reason = "Your performance indicates intermediate content would be most beneficial."
        elif skill >= 40:
            recommended = 'EASY'
            reason = "Building a strong foundation with easier content will help you progress."
        else:
            recommended = 'BEGINNER'
            reason = "Starting with beginner content will help you build confidence."

        # Adjust for topic-specific performance
        if topic:
            perf = PerformanceHistory.query.filter_by(
                user_id=user_id,
                topic=topic
            ).first()

            if perf:
                topic_skill = perf.skill_level
                if topic_skill < skill - 20:
                    # Weaker in this specific topic
                    idx = max(0, self.DIFFICULTY_LEVELS.index(recommended) - 1)
                    recommended = self.DIFFICULTY_LEVELS[idx]
                    reason = f"Your performance in {topic} suggests starting at a lower level."
                elif topic_skill > skill + 20:
                    # Stronger in this topic
                    idx = min(len(self.DIFFICULTY_LEVELS) - 1, self.DIFFICULTY_LEVELS.index(recommended) + 1)
                    recommended = self.DIFFICULTY_LEVELS[idx]
                    reason = f"Your strong performance in {topic} means you can handle more challenge."

        return {
            'recommended_difficulty': recommended,
            'reason': reason,
            'skill_level': skill,
            'velocity': profile['velocity_classification'],
            'can_increase': recommended != self.DIFFICULTY_LEVELS[-1],
            'can_decrease': recommended != self.DIFFICULTY_LEVELS[0]
        }

    # ==================== PERSONALIZED CONTENT GENERATION ====================

    def generate_personalized_content(
        self,
        user_id: int,
        content_type: str,
        topic: str,
        **kwargs
    ) -> Dict:
        """
        Generate personalized content based on user profile.

        Args:
            user_id: User ID
            content_type: COURSE, QUIZ, or ASSIGNMENT
            topic: Content topic
            **kwargs: Additional parameters

        Returns:
            Generated content
        """
        ai_service = self._get_ai_service()
        profile = self.get_user_learning_profile(user_id)
        perf_history = self.get_performance_history_dict(user_id)

        if content_type == 'COURSE':
            return ai_service.generate_personalized_course(
                topic=topic,
                user_profile=profile,
                performance_history=perf_history,
                weeks=kwargs.get('weeks', 8),
                force_regenerate=kwargs.get('force_regenerate', False)
            )

        elif content_type == 'QUIZ':
            return ai_service.generate_adaptive_quiz(
                topic=topic,
                user_performance=perf_history,
                learning_style=profile['learning_style'],
                question_count=kwargs.get('question_count', 10),
                force_regenerate=kwargs.get('force_regenerate', False)
            )

        elif content_type == 'ASSIGNMENT':
            return ai_service.generate_personalized_assignment(
                topic=topic,
                lesson_content=kwargs.get('lesson_content', ''),
                user_profile=profile,
                performance_history=perf_history,
                force_regenerate=kwargs.get('force_regenerate', False)
            )

        elif content_type == 'LEARNING_PATH':
            return ai_service.generate_learning_path(
                target_skill=topic,
                current_level=self._skill_to_level(profile['skill_level']),
                learning_style=profile['learning_style'],
                weeks=kwargs.get('weeks', 12),
                user_profile=profile
            )

        raise ValueError(f"Unknown content type: {content_type}")

    def _skill_to_level(self, skill: float) -> str:
        """Convert skill level (0-100) to level name"""
        if skill >= 80:
            return 'ADVANCED'
        elif skill >= 60:
            return 'INTERMEDIATE'
        elif skill >= 40:
            return 'BEGINNER_PLUS'
        else:
            return 'BEGINNER'

    # ==================== LEARNING INSIGHTS ====================

    def get_learning_insights(self, user_id: int) -> Dict:
        """
        Get AI-powered learning insights for the user.

        Returns:
            Insights and recommendations
        """
        profile = self.get_user_learning_profile(user_id)
        perf_history = self.get_performance_history_dict(user_id)
        review_schedule = self.get_review_schedule(user_id)

        insights = []
        recommendations = []

        # Learning style insight
        if profile['style_confidence'] >= 70:
            insights.append({
                'type': 'LEARNING_STYLE',
                'message': f"You're a {profile['learning_style']} learner with {profile['style_confidence']:.0f}% confidence.",
                'detail': self._get_style_advice(profile['learning_style'])
            })

        # Velocity insight
        if profile['velocity_classification'] == 'FAST':
            insights.append({
                'type': 'VELOCITY',
                'message': "You learn faster than average!",
                'detail': "Consider taking on more challenging content or covering more material."
            })
        elif profile['velocity_classification'] == 'SLOW':
            insights.append({
                'type': 'VELOCITY',
                'message': "You prefer a thorough learning pace.",
                'detail': "This is great for deep understanding. Consider breaking content into smaller sessions."
            })

        # Knowledge gaps
        if profile['weak_areas']:
            insights.append({
                'type': 'KNOWLEDGE_GAP',
                'message': f"Areas to focus on: {', '.join(profile['weak_areas'][:3])}",
                'detail': "Targeted practice in these areas will improve your overall performance."
            })

        # Review reminder
        if review_schedule['topics_due_count'] > 0:
            recommendations.append({
                'type': 'REVIEW',
                'priority': 'HIGH',
                'message': f"{review_schedule['topics_due_count']} topics are due for review",
                'action': 'Start review session'
            })

        # Engagement suggestion
        if profile['engagement_score'] < 50:
            recommendations.append({
                'type': 'ENGAGEMENT',
                'priority': 'MEDIUM',
                'message': "Try shorter, more frequent learning sessions",
                'action': 'Set learning reminders'
            })

        # Difficulty suggestion
        difficulty_rec = self.get_recommended_difficulty(user_id)
        if difficulty_rec['can_increase'] and profile['avg_quiz_score'] > 85:
            recommendations.append({
                'type': 'CHALLENGE',
                'priority': 'LOW',
                'message': "You're ready for more challenging content!",
                'action': 'Explore advanced courses'
            })

        return {
            'user_id': user_id,
            'generated_at': datetime.utcnow().isoformat(),
            'profile_summary': {
                'learning_style': profile['learning_style'],
                'skill_level': profile['skill_level'],
                'velocity': profile['velocity_classification'],
                'engagement': profile['engagement_score']
            },
            'insights': insights,
            'recommendations': recommendations,
            'review_status': {
                'topics_due': review_schedule['topics_due_count'],
                'mastered_topics': len(review_schedule['mastered_topics'])
            }
        }

    def _get_style_advice(self, style: str) -> str:
        """Get learning advice for a style"""
        advice = {
            'VISUAL': "Look for video content, diagrams, and visual representations. Create mind maps and flowcharts.",
            'AUDITORY': "Try explaining concepts aloud, join discussions, and use audio resources like podcasts.",
            'KINESTHETIC': "Focus on hands-on projects, coding exercises, and practical applications.",
            'READING_WRITING': "Take detailed notes, read documentation, and write summaries of what you learn.",
            'MULTIMODAL': "Mix different learning methods - videos, reading, practice - to reinforce concepts."
        }
        return advice.get(style, advice['MULTIMODAL'])

    # ==================== CONFIDENCE-AWARE DIFFICULTY ADAPTATION ====================

    def get_confidence_aware_difficulty(
        self,
        user_id: int,
        topic: str = None,
        include_analysis: bool = True
    ) -> Dict:
        """
        Get difficulty recommendation with confidence-aware adaptation.

        Uses performance history, attempt analysis, and VARK confidence
        to make nuanced difficulty adjustments.
        """
        from models import QuizAttempt, PerformanceHistory, LearningStyle

        profile = self.get_user_learning_profile(user_id)

        # Get recent quiz attempts (last 10)
        recent_attempts = QuizAttempt.query.filter_by(
            user_id=user_id
        ).order_by(
            QuizAttempt.completed_at.desc()
        ).limit(10).all()

        # Calculate attempt-based metrics
        if recent_attempts:
            scores = [a.score for a in recent_attempts if a.score is not None]
            recent_avg = sum(scores) / len(scores) if scores else 50

            # Calculate performance trend
            if len(scores) >= 3:
                first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
                second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
                trend = 'improving' if second_half > first_half + 5 else (
                    'declining' if second_half < first_half - 5 else 'stable'
                )
            else:
                trend = 'insufficient_data'

            # Calculate consistency (standard deviation)
            if len(scores) > 1:
                mean = sum(scores) / len(scores)
                variance = sum((x - mean) ** 2 for x in scores) / len(scores)
                consistency = max(0, 100 - (variance ** 0.5))  # Higher = more consistent
            else:
                consistency = 50
        else:
            recent_avg = 50
            trend = 'no_data'
            consistency = 50

        # Get VARK confidence
        learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
        vark_confidence = learning_style.confidence if learning_style else 0

        # Topic-specific performance
        topic_skill = 50
        topic_attempts = 0
        if topic:
            perf = PerformanceHistory.query.filter_by(
                user_id=user_id,
                topic=topic
            ).first()
            if perf:
                topic_skill = perf.skill_level or 50
                topic_attempts = perf.total_attempts or 0

        # Calculate confidence-adjusted difficulty
        base_difficulty = self._calculate_base_difficulty(recent_avg, topic_skill)

        # Confidence factors
        performance_confidence = min(100, len(recent_attempts) * 10)  # More attempts = more confidence
        topic_confidence = min(100, topic_attempts * 15)

        # Overall confidence (0-100)
        overall_confidence = (
            performance_confidence * 0.4 +
            topic_confidence * 0.3 +
            vark_confidence * 0.3
        )

        # Adjust difficulty based on confidence and trend
        adjusted_difficulty = base_difficulty

        # Low confidence = stay conservative
        if overall_confidence < 40:
            # Stay at current level or slightly lower
            if adjusted_difficulty in ['ADVANCED', 'EXPERT']:
                adjusted_difficulty = 'INTERMEDIATE'
        # High confidence + improving = can push harder
        elif overall_confidence >= 70 and trend == 'improving':
            difficulty_index = self.DIFFICULTY_LEVELS.index(adjusted_difficulty)
            if difficulty_index < len(self.DIFFICULTY_LEVELS) - 1:
                adjusted_difficulty = self.DIFFICULTY_LEVELS[difficulty_index + 1]
        # High confidence + declining = ease up
        elif overall_confidence >= 60 and trend == 'declining':
            difficulty_index = self.DIFFICULTY_LEVELS.index(adjusted_difficulty)
            if difficulty_index > 0:
                adjusted_difficulty = self.DIFFICULTY_LEVELS[difficulty_index - 1]

        # Consistency adjustment
        if consistency < 40:
            # Inconsistent performance = might need consolidation
            difficulty_index = self.DIFFICULTY_LEVELS.index(adjusted_difficulty)
            if difficulty_index > 1:
                adjusted_difficulty = self.DIFFICULTY_LEVELS[difficulty_index - 1]

        result = {
            'user_id': user_id,
            'topic': topic,
            'recommended_difficulty': adjusted_difficulty,
            'overall_confidence': round(overall_confidence, 1),
            'can_increase': adjusted_difficulty != self.DIFFICULTY_LEVELS[-1],
            'can_decrease': adjusted_difficulty != self.DIFFICULTY_LEVELS[0]
        }

        if include_analysis:
            result['analysis'] = {
                'recent_avg_score': round(recent_avg, 1),
                'performance_trend': trend,
                'consistency_score': round(consistency, 1),
                'topic_skill_level': round(topic_skill, 1),
                'topic_attempts': topic_attempts,
                'vark_confidence': round(vark_confidence, 1),
                'performance_confidence': round(performance_confidence, 1),
                'topic_confidence': round(topic_confidence, 1)
            }

            # Generate recommendations
            result['recommendations'] = self._generate_difficulty_recommendations(
                trend, consistency, overall_confidence, adjusted_difficulty
            )

        return result

    def _calculate_base_difficulty(self, recent_avg: float, topic_skill: float) -> str:
        """Calculate base difficulty from scores"""
        combined_score = (recent_avg * 0.6 + topic_skill * 0.4)

        if combined_score >= 85:
            return 'EXPERT'
        elif combined_score >= 75:
            return 'ADVANCED'
        elif combined_score >= 60:
            return 'INTERMEDIATE'
        elif combined_score >= 45:
            return 'EASY'
        else:
            return 'BEGINNER'

    def _generate_difficulty_recommendations(
        self,
        trend: str,
        consistency: float,
        confidence: float,
        current_difficulty: str
    ) -> List[Dict]:
        """Generate recommendations based on difficulty analysis"""
        recommendations = []

        if trend == 'improving':
            recommendations.append({
                'type': 'POSITIVE',
                'message': "Great progress! Your scores are improving.",
                'action': "Consider challenging yourself with harder content."
            })
        elif trend == 'declining':
            recommendations.append({
                'type': 'ATTENTION',
                'message': "Your recent scores show a slight decline.",
                'action': "Review fundamentals before moving forward."
            })

        if consistency < 40:
            recommendations.append({
                'type': 'SUGGESTION',
                'message': "Your performance varies significantly.",
                'action': "Focus on consistent practice to build a strong foundation."
            })

        if confidence < 40:
            recommendations.append({
                'type': 'INFO',
                'message': "We need more data to accurately assess your level.",
                'action': "Complete more quizzes to improve personalization."
            })

        return recommendations

    # ==================== CONCEPT-WISE MASTERY TRACKING ====================

    def update_concept_mastery(
        self,
        user_id: int,
        concept_name: str,
        correct: bool,
        topic: str = None,
        course_id: int = None,
        time_spent_seconds: int = 0,
        misconception: Dict = None
    ) -> Dict:
        """
        Update mastery for a specific concept.

        Args:
            user_id: User ID
            concept_name: Name of the concept
            correct: Whether the attempt was correct
            topic: Parent topic
            course_id: Associated course
            time_spent_seconds: Time spent on this attempt
            misconception: Optional misconception data {"incorrect": "...", "correct": "..."}
        """
        from models import ConceptMastery

        try:
            # Get or create mastery record
            mastery = ConceptMastery.query.filter_by(
                user_id=user_id,
                concept_name=concept_name,
                topic=topic
            ).first()

            if not mastery:
                mastery = ConceptMastery(
                    user_id=user_id,
                    concept_name=concept_name,
                    topic=topic,
                    course_id=course_id,
                    first_exposure=datetime.utcnow()
                )
                db.session.add(mastery)

            # Update attempt counts
            mastery.attempts = (mastery.attempts or 0) + 1
            if correct:
                mastery.correct_attempts = (mastery.correct_attempts or 0) + 1

            # Calculate mastery level using weighted formula
            accuracy = (mastery.correct_attempts / mastery.attempts) * 100

            # Factor in recency - recent correct answers boost mastery more
            recency_weight = 0.3
            current_mastery = mastery.mastery_level or 0.0  # Handle None for new records
            if correct:
                new_mastery = current_mastery * (1 - recency_weight) + 100 * recency_weight
            else:
                new_mastery = current_mastery * (1 - recency_weight) + 0 * recency_weight

            # Blend with accuracy
            mastery.mastery_level = (new_mastery * 0.6 + accuracy * 0.4)

            # Update confidence (based on number of attempts)
            mastery.confidence = min(100, mastery.attempts * 10)

            # Update learning curve
            curve = json.loads(mastery.learning_curve) if mastery.learning_curve else []
            curve.append({
                'date': datetime.utcnow().isoformat(),
                'score': 100 if correct else 0,
                'mastery_level': mastery.mastery_level
            })
            mastery.learning_curve = json.dumps(curve[-20:])  # Keep last 20 points

            # Update time tracking
            mastery.total_practice_time_seconds = (mastery.total_practice_time_seconds or 0) + time_spent_seconds
            mastery.last_practiced = datetime.utcnow()

            # Check if mastered
            if mastery.mastery_level >= 80 and not mastery.time_to_mastery_minutes:
                if mastery.first_exposure:
                    time_to_master = (datetime.utcnow() - mastery.first_exposure).total_seconds() / 60
                    mastery.time_to_mastery_minutes = int(time_to_master)

            # Calculate difficulty rating
            if mastery.attempts >= 3:
                # Higher accuracy = lower difficulty for this user
                mastery.difficulty_rating = max(0, 100 - accuracy)

            # Track misconceptions
            if misconception and not correct:
                misconceptions = json.loads(mastery.misconceptions) if mastery.misconceptions else []
                # Check if this misconception already exists
                existing = next((m for m in misconceptions if m.get('incorrect') == misconception.get('incorrect')), None)
                if existing:
                    existing['count'] = existing.get('count', 1) + 1
                else:
                    misconceptions.append({
                        'incorrect': misconception.get('incorrect'),
                        'correct': misconception.get('correct'),
                        'count': 1,
                        'first_seen': datetime.utcnow().isoformat()
                    })
                mastery.misconceptions = json.dumps(misconceptions[-10:])  # Keep last 10

            db.session.commit()

            return mastery.to_dict()

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def get_concept_mastery_report(self, user_id: int, topic: str = None) -> Dict:
        """
        Get comprehensive concept mastery report.
        """
        from models import ConceptMastery

        try:
            query = ConceptMastery.query.filter_by(user_id=user_id)
            if topic:
                query = query.filter_by(topic=topic)

            masteries = query.all()

            if not masteries:
                return {
                    'user_id': user_id,
                    'message': 'No concept mastery data available',
                    'concepts': []
                }

            # Categorize concepts
            mastered = []
            learning = []
            struggling = []
            not_started = []

            for m in masteries:
                concept_data = {
                    'concept': m.concept_name,
                    'topic': m.topic,
                    'mastery_level': round(m.mastery_level or 0, 1),
                    'accuracy': round((m.correct_attempts or 0) / m.attempts * 100, 1) if m.attempts else 0,
                    'attempts': m.attempts or 0,
                    'confidence': m.confidence or 0,
                    'difficulty_rating': m.difficulty_rating,
                    'last_practiced': m.last_practiced.isoformat() if m.last_practiced else None
                }

                if (m.mastery_level or 0) >= 80:
                    mastered.append(concept_data)
                elif (m.mastery_level or 0) >= 50:
                    learning.append(concept_data)
                elif m.attempts and m.attempts > 0:
                    struggling.append(concept_data)
                else:
                    not_started.append(concept_data)

            # Get common misconceptions
            all_misconceptions = []
            for m in masteries:
                if m.misconceptions:
                    try:
                        miscons = json.loads(m.misconceptions)
                        for mis in miscons:
                            mis['concept'] = m.concept_name
                            all_misconceptions.append(mis)
                    except:
                        pass

            # Sort by frequency
            all_misconceptions.sort(key=lambda x: x.get('count', 0), reverse=True)

            # Calculate overall metrics
            total_concepts = len(masteries)
            avg_mastery = sum(m.mastery_level or 0 for m in masteries) / total_concepts if total_concepts else 0

            return {
                'user_id': user_id,
                'topic_filter': topic,
                'summary': {
                    'total_concepts': total_concepts,
                    'mastered_count': len(mastered),
                    'learning_count': len(learning),
                    'struggling_count': len(struggling),
                    'average_mastery': round(avg_mastery, 1),
                    'mastery_rate': round(len(mastered) / total_concepts * 100, 1) if total_concepts else 0
                },
                'concepts': {
                    'mastered': sorted(mastered, key=lambda x: x['mastery_level'], reverse=True),
                    'learning': sorted(learning, key=lambda x: x['mastery_level'], reverse=True),
                    'struggling': sorted(struggling, key=lambda x: x['mastery_level']),
                    'not_started': not_started
                },
                'common_misconceptions': all_misconceptions[:10],
                'recommendations': self._generate_mastery_recommendations(
                    mastered, learning, struggling, all_misconceptions
                )
            }

        except Exception as e:
            return {'error': str(e)}

    def _generate_mastery_recommendations(
        self,
        mastered: List,
        learning: List,
        struggling: List,
        misconceptions: List
    ) -> List[Dict]:
        """Generate recommendations based on mastery analysis"""
        recommendations = []

        if struggling:
            recommendations.append({
                'type': 'FOCUS',
                'priority': 'HIGH',
                'message': f"Focus on these struggling concepts: {', '.join([c['concept'] for c in struggling[:3]])}",
                'concepts': [c['concept'] for c in struggling[:3]]
            })

        if misconceptions:
            recommendations.append({
                'type': 'REVIEW',
                'priority': 'MEDIUM',
                'message': "Review these common misconceptions to avoid repeated errors",
                'misconceptions': misconceptions[:3]
            })

        if mastered and not struggling:
            recommendations.append({
                'type': 'ADVANCE',
                'priority': 'LOW',
                'message': "Great progress! Consider moving to more advanced topics."
            })

        if learning:
            # Find concepts close to mastery
            close_to_mastery = [c for c in learning if c['mastery_level'] >= 70]
            if close_to_mastery:
                recommendations.append({
                    'type': 'PRACTICE',
                    'priority': 'MEDIUM',
                    'message': f"These concepts are close to mastery with a little more practice: {', '.join([c['concept'] for c in close_to_mastery[:3]])}",
                    'concepts': [c['concept'] for c in close_to_mastery[:3]]
                })

        return recommendations


# Singleton instance
_personalization_service = None

def get_personalization_service() -> PersonalizationService:
    """Get the singleton personalization service instance"""
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService()
    return _personalization_service
