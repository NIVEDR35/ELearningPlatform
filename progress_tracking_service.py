"""
Progress Tracking Service
Provides comprehensive real-time progress tracking at all levels:
- Lesson level (content, video, quiz, assignment)
- Course level (aggregated progress)
- Learning velocity calculation
- Knowledge gap identification
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from models import (
    db, User, Course, Module, Lesson, LessonProgress, CourseProgress,
    QuizAttempt, PerformanceHistory, LearningStyle, LearningBehavior,
    UserInteraction
)


class ProgressTrackingService:
    """Comprehensive progress tracking at all levels"""

    # Weights for lesson completion calculation
    COMPLETION_WEIGHTS = {
        'content_viewed': 0.30,
        'video_watched': 0.25,
        'quiz_passed': 0.25,
        'assignment_completed': 0.20
    }

    # Minimum data points for reliable velocity calculation
    MIN_VELOCITY_DATA_POINTS = 5

    # Knowledge gap threshold (below this accuracy = weak area)
    KNOWLEDGE_GAP_THRESHOLD = 0.6

    # Mastery threshold (above this = strong area)
    MASTERY_THRESHOLD = 0.8

    def __init__(self):
        pass

    # ==================== LESSON PROGRESS TRACKING ====================

    def track_lesson_progress(
        self,
        user_id: int,
        lesson_id: int,
        action: str,
        duration_seconds: int = 0,
        metadata: Dict = None
    ) -> Dict:
        """
        Track granular lesson progress.

        Args:
            user_id: User ID
            lesson_id: Lesson ID
            action: Type of action (CONTENT_VIEW, VIDEO_WATCH, QUIZ_ATTEMPT, etc.)
            duration_seconds: Time spent on action
            metadata: Additional action metadata

        Returns:
            Updated progress dict
        """
        metadata = metadata or {}

        # Get or create progress record
        progress = LessonProgress.query.filter_by(
            user_id=user_id,
            lesson_id=lesson_id
        ).first()

        if not progress:
            # Get lesson to find course_id
            lesson = Lesson.query.get(lesson_id)
            course_id = lesson.module.course_id if lesson and lesson.module else None

            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                course_id=course_id,
                started_at=datetime.utcnow()
            )
            db.session.add(progress)

        # Update based on action type
        if action == 'CONTENT_VIEW':
            progress.content_viewed = True
            progress.time_spent_seconds = (progress.time_spent_seconds or 0) + duration_seconds

        elif action == 'VIDEO_WATCH':
            progress.video_watched = True
            progress.content_viewed = True  # Video watching counts as content engagement
            watch_percentage = metadata.get('percentage', 50)  # Default 50% if not specified
            progress.video_watch_percentage = max(
                progress.video_watch_percentage or 0,
                watch_percentage
            )
            progress.time_spent_seconds = (progress.time_spent_seconds or 0) + duration_seconds

        elif action == 'VIDEO_COMPLETE':
            progress.video_watched = True
            progress.video_watch_percentage = 100.0

        elif action == 'QUIZ_ATTEMPT':
            progress.quiz_attempted = True
            progress.quiz_attempts = (progress.quiz_attempts or 0) + 1
            score = metadata.get('score', 0)
            progress.quiz_score = score
            progress.best_quiz_score = max(progress.best_quiz_score or 0, score)
            if score >= metadata.get('passing_score', 70):
                progress.quiz_passed = True

        elif action == 'ASSIGNMENT_SUBMIT':
            progress.assignment_completed = True
            progress.assignment_score = metadata.get('score')
            progress.assignment_submitted_at = datetime.utcnow()

        elif action == 'CODE_EXAMPLE_RUN':
            progress.code_example_run = True

        elif action == 'INTERACTIVE_COMPLETE':
            progress.interactive_completed = True

        elif action == 'BOOKMARK':
            progress.is_bookmarked = metadata.get('bookmarked', True)

        elif action == 'NOTE_ADD':
            existing_notes = progress.user_notes or ''
            new_note = metadata.get('note', '')
            if new_note:
                progress.user_notes = f"{existing_notes}\n\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{new_note}"

        elif action == 'LESSON_COMPLETE':
            # Manually mark the lesson as complete
            progress.content_viewed = True
            progress.video_watched = True
            progress.video_watch_percentage = 100.0
            progress.status = 'COMPLETED'
            progress.completion_percentage = 100.0
            if not progress.completed_at:
                progress.completed_at = datetime.utcnow()

        # Calculate completion percentage
        progress.completion_percentage = self._calculate_lesson_completion(progress)

        # Update status
        if progress.completion_percentage >= 100:
            progress.status = 'COMPLETED'
            if not progress.completed_at:
                progress.completed_at = datetime.utcnow()
        elif progress.completion_percentage > 0:
            progress.status = 'IN_PROGRESS'

        progress.last_accessed = datetime.utcnow()

        db.session.commit()

        # Update course-level progress
        if progress.course_id:
            self._update_course_progress(user_id, progress.course_id)

        # Update learning velocity if lesson completed
        if progress.status == 'COMPLETED':
            self._update_learning_velocity(user_id, lesson_id, progress.time_spent_seconds)

        return progress.to_dict()

    def _calculate_lesson_completion(self, progress: LessonProgress) -> float:
        """Calculate lesson completion percentage based on engagement"""
        total = 0.0

        # Get lesson to check what content exists
        lesson = Lesson.query.get(progress.lesson_id)
        if not lesson:
            return 0.0

        available_weights = {}
        total_weight = 0.0

        # Content viewing (always available)
        available_weights['content_viewed'] = self.COMPLETION_WEIGHTS['content_viewed']
        total_weight += self.COMPLETION_WEIGHTS['content_viewed']

        # Video (if available)
        if lesson.video_url or lesson.video_id:
            available_weights['video_watched'] = self.COMPLETION_WEIGHTS['video_watched']
            total_weight += self.COMPLETION_WEIGHTS['video_watched']

        # Quiz (if available)
        if lesson.quiz_questions:
            available_weights['quiz_passed'] = self.COMPLETION_WEIGHTS['quiz_passed']
            total_weight += self.COMPLETION_WEIGHTS['quiz_passed']

        # Assignment (if available)
        if lesson.assignment:
            available_weights['assignment_completed'] = self.COMPLETION_WEIGHTS['assignment_completed']
            total_weight += self.COMPLETION_WEIGHTS['assignment_completed']

        # Normalize weights
        if total_weight > 0:
            for key in available_weights:
                available_weights[key] /= total_weight

        # Calculate completion
        if progress.content_viewed and 'content_viewed' in available_weights:
            total += available_weights['content_viewed'] * 100

        if progress.video_watched and 'video_watched' in available_weights:
            # Partial credit for video watch percentage
            video_credit = (progress.video_watch_percentage or 0) / 100
            total += available_weights['video_watched'] * 100 * video_credit

        if progress.quiz_passed and 'quiz_passed' in available_weights:
            total += available_weights['quiz_passed'] * 100

        if progress.assignment_completed and 'assignment_completed' in available_weights:
            total += available_weights['assignment_completed'] * 100

        return min(total, 100.0)

    def _update_course_progress(self, user_id: int, course_id: int) -> None:
        """Update course-level progress based on lesson progress"""
        # Get or create course progress
        course_progress = CourseProgress.query.filter_by(
            user_id=user_id,
            course_id=course_id
        ).first()

        if not course_progress:
            course_progress = CourseProgress(
                user_id=user_id,
                course_id=course_id,
                enrolled_at=datetime.utcnow()
            )
            db.session.add(course_progress)

        # Get course structure
        course = Course.query.get(course_id)
        if not course:
            return

        # Count total lessons
        total_lessons = db.session.query(Lesson).join(Module).filter(
            Module.course_id == course_id
        ).count()

        course_progress.total_lessons = total_lessons
        course_progress.total_modules = len(course.modules)

        # Count completed lessons
        completed_lessons = LessonProgress.query.filter_by(
            user_id=user_id,
            course_id=course_id,
            status='COMPLETED'
        ).count()

        course_progress.lessons_completed = completed_lessons

        # Calculate completion percentage
        if total_lessons > 0:
            course_progress.completion_percentage = (completed_lessons / total_lessons) * 100
        else:
            course_progress.completion_percentage = 0

        # Count completed modules
        modules_completed = 0
        for module in course.modules:
            module_lessons = len(module.lessons)
            if module_lessons > 0:
                completed_in_module = LessonProgress.query.filter(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id.in_([l.id for l in module.lessons]),
                    LessonProgress.status == 'COMPLETED'
                ).count()
                if completed_in_module >= module_lessons:
                    modules_completed += 1

        course_progress.modules_completed = modules_completed

        # Get quiz stats
        quiz_stats = db.session.query(
            func.count(QuizAttempt.id),
            func.count(QuizAttempt.id).filter(QuizAttempt.passed == True),
            func.avg(QuizAttempt.score)
        ).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.course_id == course_id
        ).first()

        course_progress.quizzes_attempted = quiz_stats[0] or 0
        course_progress.quizzes_passed = quiz_stats[1] or 0
        course_progress.average_quiz_score = quiz_stats[2] or 0

        # Total time spent
        total_time = db.session.query(
            func.sum(LessonProgress.time_spent_seconds)
        ).filter(
            LessonProgress.user_id == user_id,
            LessonProgress.course_id == course_id
        ).scalar() or 0

        course_progress.total_time_spent_seconds = total_time

        # Update status
        if course_progress.completion_percentage >= 100:
            course_progress.status = 'COMPLETED'
            if not course_progress.completed_at:
                course_progress.completed_at = datetime.utcnow()
        elif course_progress.completion_percentage > 0:
            course_progress.status = 'IN_PROGRESS'
            if not course_progress.started_at:
                course_progress.started_at = datetime.utcnow()

        course_progress.last_accessed = datetime.utcnow()

        db.session.commit()

    def _update_learning_velocity(self, user_id: int, lesson_id: int, time_spent: int) -> None:
        """Update learning velocity based on lesson completion time"""
        lesson = Lesson.query.get(lesson_id)
        if not lesson or not lesson.duration_minutes:
            return

        expected_seconds = lesson.duration_minutes * 60
        if expected_seconds <= 0 or time_spent <= 0:
            return

        # Calculate velocity for this lesson
        velocity = expected_seconds / time_spent  # >1 = faster, <1 = slower

        # Update performance history for the topic
        topic = lesson.title  # Could be improved with better topic extraction
        perf = PerformanceHistory.query.filter_by(
            user_id=user_id,
            topic=topic
        ).first()

        if not perf:
            perf = PerformanceHistory(
                user_id=user_id,
                topic=topic,
                learning_velocity=velocity
            )
            db.session.add(perf)
        else:
            # Moving average of velocity
            old_velocity = perf.learning_velocity or 1.0
            perf.learning_velocity = (old_velocity * 0.7) + (velocity * 0.3)

        db.session.commit()

    # ==================== LEARNING VELOCITY ====================

    def calculate_learning_velocity(self, user_id: int) -> Dict:
        """
        Calculate how fast the user learns compared to expected time.

        Returns:
            Dict with velocity metrics
        """
        # Get completed lessons with time data
        completions = db.session.query(
            LessonProgress.lesson_id,
            LessonProgress.time_spent_seconds,
            Lesson.duration_minutes
        ).join(Lesson).filter(
            LessonProgress.user_id == user_id,
            LessonProgress.status == 'COMPLETED',
            LessonProgress.time_spent_seconds > 0,
            Lesson.duration_minutes > 0
        ).all()

        if len(completions) < self.MIN_VELOCITY_DATA_POINTS:
            return {
                'velocity': 1.0,
                'classification': 'NORMAL',
                'data_points': len(completions),
                'sufficient_data': False,
                'message': f'Need at least {self.MIN_VELOCITY_DATA_POINTS} completed lessons for accurate velocity'
            }

        # Calculate velocity ratios
        ratios = []
        for lesson_id, actual_seconds, expected_minutes in completions:
            expected_seconds = expected_minutes * 60
            ratio = expected_seconds / actual_seconds
            # Cap extreme values
            ratio = max(0.2, min(5.0, ratio))
            ratios.append(ratio)

        avg_velocity = sum(ratios) / len(ratios)

        # Classify velocity
        if avg_velocity > 1.5:
            classification = 'FAST'
            message = 'You learn faster than average! Consider more challenging content.'
        elif avg_velocity > 1.2:
            classification = 'ABOVE_AVERAGE'
            message = 'You learn slightly faster than expected.'
        elif avg_velocity < 0.6:
            classification = 'SLOW'
            message = 'Take your time - thorough learning is valuable.'
        elif avg_velocity < 0.8:
            classification = 'BELOW_AVERAGE'
            message = 'You prefer a more thorough pace.'
        else:
            classification = 'NORMAL'
            message = 'Your learning pace is typical.'

        return {
            'velocity': round(avg_velocity, 2),
            'classification': classification,
            'data_points': len(ratios),
            'sufficient_data': True,
            'message': message,
            'percentile': self._velocity_to_percentile(avg_velocity)
        }

    def _velocity_to_percentile(self, velocity: float) -> int:
        """Convert velocity to percentile (0-100)"""
        # Assuming normal distribution around 1.0
        if velocity >= 2.0:
            return 95
        elif velocity >= 1.5:
            return 85
        elif velocity >= 1.2:
            return 70
        elif velocity >= 1.0:
            return 55
        elif velocity >= 0.8:
            return 40
        elif velocity >= 0.6:
            return 25
        else:
            return 10

    # ==================== KNOWLEDGE GAP IDENTIFICATION ====================

    def identify_knowledge_gaps(self, user_id: int) -> Dict:
        """
        Analyze quiz and assignment performance to identify knowledge gaps.

        Returns:
            Dict with weak and strong areas
        """
        # Get all quiz attempts with performance details
        attempts = QuizAttempt.query.filter_by(user_id=user_id).all()

        topic_performance = {}
        concept_performance = {}

        for attempt in attempts:
            # Track by topic
            topic = attempt.quiz_topic or 'General'
            if topic not in topic_performance:
                topic_performance[topic] = {'correct': 0, 'total': 0, 'scores': []}

            topic_performance[topic]['scores'].append(attempt.score)
            topic_performance[topic]['total'] += attempt.total_questions or 0
            topic_performance[topic]['correct'] += attempt.correct_answers or 0

            # Track by concept (from question performance)
            if attempt.question_performance:
                try:
                    q_perf = json.loads(attempt.question_performance)
                    for q in q_perf:
                        concept = q.get('concept', 'general')
                        if concept not in concept_performance:
                            concept_performance[concept] = {'correct': 0, 'total': 0}
                        concept_performance[concept]['total'] += 1
                        if q.get('correct', False):
                            concept_performance[concept]['correct'] += 1
                except (json.JSONDecodeError, TypeError):
                    pass

        # Identify weak and strong areas
        weak_areas = []
        strong_areas = []
        improving_areas = []

        for topic, stats in topic_performance.items():
            if stats['total'] >= 3:  # Need at least 3 questions
                accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0

                area_data = {
                    'topic': topic,
                    'accuracy': round(accuracy * 100, 1),
                    'average_score': round(avg_score, 1),
                    'attempts': len(stats['scores']),
                    'total_questions': stats['total']
                }

                if accuracy < self.KNOWLEDGE_GAP_THRESHOLD:
                    weak_areas.append(area_data)
                elif accuracy >= self.MASTERY_THRESHOLD:
                    strong_areas.append(area_data)

                # Check if improving (last score > first score)
                if len(stats['scores']) >= 2:
                    if stats['scores'][-1] > stats['scores'][0]:
                        improving_areas.append({
                            'topic': topic,
                            'improvement': stats['scores'][-1] - stats['scores'][0]
                        })

        # Sort by accuracy
        weak_areas.sort(key=lambda x: x['accuracy'])
        strong_areas.sort(key=lambda x: x['accuracy'], reverse=True)
        improving_areas.sort(key=lambda x: x['improvement'], reverse=True)

        # Also analyze concept-level gaps
        concept_gaps = []
        concept_strengths = []

        for concept, stats in concept_performance.items():
            if stats['total'] >= 2:
                accuracy = stats['correct'] / stats['total']
                if accuracy < self.KNOWLEDGE_GAP_THRESHOLD:
                    concept_gaps.append({
                        'concept': concept,
                        'accuracy': round(accuracy * 100, 1),
                        'questions_seen': stats['total']
                    })
                elif accuracy >= self.MASTERY_THRESHOLD:
                    concept_strengths.append({
                        'concept': concept,
                        'accuracy': round(accuracy * 100, 1),
                        'questions_seen': stats['total']
                    })

        return {
            'weak_areas': weak_areas[:10],  # Top 10 weak areas
            'strong_areas': strong_areas[:10],  # Top 10 strong areas
            'improving_areas': improving_areas[:5],
            'concept_gaps': concept_gaps[:10],
            'concept_strengths': concept_strengths[:10],
            'total_topics_analyzed': len(topic_performance),
            'total_concepts_analyzed': len(concept_performance),
            'overall_accuracy': self._calculate_overall_accuracy(topic_performance)
        }

    def _calculate_overall_accuracy(self, topic_performance: Dict) -> float:
        """Calculate overall accuracy across all topics"""
        total_correct = sum(t['correct'] for t in topic_performance.values())
        total_questions = sum(t['total'] for t in topic_performance.values())

        if total_questions == 0:
            return 0.0

        return round((total_correct / total_questions) * 100, 1)

    # ==================== COMPREHENSIVE PROGRESS REPORT ====================

    def get_comprehensive_progress(self, user_id: int, course_id: int = None) -> Dict:
        """
        Get comprehensive progress report for a user.

        Args:
            user_id: User ID
            course_id: Optional specific course

        Returns:
            Complete progress report
        """
        result = {
            'user_id': user_id,
            'generated_at': datetime.utcnow().isoformat(),
            'overall_stats': self._get_overall_stats(user_id),
            'learning_velocity': self.calculate_learning_velocity(user_id),
            'knowledge_gaps': self.identify_knowledge_gaps(user_id),
            'learning_style': self._get_learning_style_summary(user_id),
            'recent_activity': self._get_recent_activity(user_id),
            'streak_info': self._calculate_streak(user_id),
            'recommendations': self._generate_progress_recommendations(user_id)
        }

        if course_id:
            result['course_progress'] = self._get_detailed_course_progress(user_id, course_id)

        return result

    def _get_overall_stats(self, user_id: int) -> Dict:
        """Get overall learning statistics"""
        behavior = LearningBehavior.query.filter_by(user_id=user_id).first()

        # Count courses
        courses_enrolled = CourseProgress.query.filter_by(user_id=user_id).count()
        courses_completed = CourseProgress.query.filter_by(
            user_id=user_id,
            status='COMPLETED'
        ).count()
        courses_in_progress = CourseProgress.query.filter_by(
            user_id=user_id,
            status='IN_PROGRESS'
        ).count()

        # Total time
        total_time = db.session.query(
            func.sum(LessonProgress.time_spent_seconds)
        ).filter(
            LessonProgress.user_id == user_id
        ).scalar() or 0

        # Lessons completed
        lessons_completed = LessonProgress.query.filter_by(
            user_id=user_id,
            status='COMPLETED'
        ).count()

        # Quiz stats
        quiz_stats = db.session.query(
            func.count(QuizAttempt.id),
            func.avg(QuizAttempt.score)
        ).filter(
            QuizAttempt.user_id == user_id
        ).first()

        return {
            'courses_enrolled': courses_enrolled,
            'courses_completed': courses_completed,
            'courses_in_progress': courses_in_progress,
            'lessons_completed': lessons_completed,
            'total_time_hours': round(total_time / 3600, 1),
            'total_time_formatted': self._format_duration(total_time),
            'quizzes_taken': quiz_stats[0] or 0,
            'average_quiz_score': round(quiz_stats[1] or 0, 1),
            'engagement_score': behavior.engagement_score if behavior else 0
        }

    def _get_learning_style_summary(self, user_id: int) -> Dict:
        """Get learning style summary"""
        style = LearningStyle.query.filter_by(user_id=user_id).first()

        if not style:
            return {
                'dominant_style': 'UNKNOWN',
                'confidence': 0,
                'message': 'Not enough data to determine learning style'
            }

        return {
            'dominant_style': style.dominant_style,
            'visual_score': style.visual_score,
            'auditory_score': style.auditory_score,
            'kinesthetic_score': style.kinesthetic_score,
            'reading_writing_score': style.reading_writing_score,
            'confidence': style.confidence,
            'data_points': style.data_points
        }

    def _get_recent_activity(self, user_id: int, days: int = 7) -> List[Dict]:
        """Get recent activity summary"""
        since = datetime.utcnow() - timedelta(days=days)

        activities = UserInteraction.query.filter(
            UserInteraction.user_id == user_id,
            UserInteraction.timestamp >= since
        ).order_by(
            UserInteraction.timestamp.desc()
        ).limit(50).all()

        # Group by day
        daily_summary = {}
        for activity in activities:
            day = activity.timestamp.strftime('%Y-%m-%d')
            if day not in daily_summary:
                daily_summary[day] = {
                    'date': day,
                    'interactions': 0,
                    'time_spent_seconds': 0,
                    'types': []
                }

            daily_summary[day]['interactions'] += 1
            daily_summary[day]['time_spent_seconds'] += activity.duration or 0
            if activity.interaction_type not in daily_summary[day]['types']:
                daily_summary[day]['types'].append(activity.interaction_type)

        return list(daily_summary.values())

    def _calculate_streak(self, user_id: int) -> Dict:
        """Calculate learning streak"""
        today = datetime.utcnow().date()

        # Get dates with activity
        activity_dates = db.session.query(
            func.date(UserInteraction.timestamp)
        ).filter(
            UserInteraction.user_id == user_id
        ).distinct().order_by(
            func.date(UserInteraction.timestamp).desc()
        ).all()

        # Convert to date objects (SQLite returns strings)
        activity_dates = []
        for d in activity_dates:
            date_val = d[0]
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
            elif isinstance(date_val, datetime):
                date_val = date_val.date()
            activity_dates.append(date_val)

        if not activity_dates:
            return {'current_streak': 0, 'longest_streak': 0, 'active_today': False}

        # Calculate current streak
        current_streak = 0
        check_date = today

        for date in activity_dates:
            if date == check_date:
                current_streak += 1
                check_date -= timedelta(days=1)
            elif date == check_date - timedelta(days=1):
                # Allow one day gap
                check_date = date
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        # Calculate longest streak
        longest_streak = current_streak
        temp_streak = 1

        for i in range(1, len(activity_dates)):
            diff = (activity_dates[i-1] - activity_dates[i]).days
            if diff <= 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1

        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'active_today': today in activity_dates
        }

    def _generate_progress_recommendations(self, user_id: int) -> List[Dict]:
        """Generate recommendations based on progress"""
        recommendations = []

        # Check knowledge gaps
        gaps = self.identify_knowledge_gaps(user_id)
        if gaps['weak_areas']:
            recommendations.append({
                'type': 'REVIEW',
                'priority': 'HIGH',
                'message': f"Review needed: {gaps['weak_areas'][0]['topic']} ({gaps['weak_areas'][0]['accuracy']}% accuracy)",
                'action': 'Start review quiz'
            })

        # Check velocity
        velocity = self.calculate_learning_velocity(user_id)
        if velocity['classification'] == 'FAST':
            recommendations.append({
                'type': 'CHALLENGE',
                'priority': 'MEDIUM',
                'message': 'You\'re learning fast! Try more challenging content.',
                'action': 'Explore advanced courses'
            })
        elif velocity['classification'] == 'SLOW':
            recommendations.append({
                'type': 'SUPPORT',
                'priority': 'MEDIUM',
                'message': 'Consider breaking lessons into smaller sessions.',
                'action': 'Adjust learning pace'
            })

        # Check streak
        streak = self._calculate_streak(user_id)
        if not streak['active_today']:
            recommendations.append({
                'type': 'ENGAGEMENT',
                'priority': 'LOW',
                'message': f"Keep your {streak['current_streak']}-day streak going!",
                'action': 'Complete a lesson'
            })

        return recommendations

    def get_course_progress(self, user_id: int, course_id: int) -> Dict:
        """Public method to get course progress"""
        return self._get_detailed_course_progress(user_id, course_id)

    def _get_detailed_course_progress(self, user_id: int, course_id: int) -> Dict:
        """Get detailed progress for a specific course"""
        course_progress = CourseProgress.query.filter_by(
            user_id=user_id,
            course_id=course_id
        ).first()

        if not course_progress:
            return {'enrolled': False}

        # Get lesson-level progress
        lesson_progress = LessonProgress.query.filter_by(
            user_id=user_id,
            course_id=course_id
        ).all()

        # Get course structure
        course = Course.query.get(course_id)

        modules_progress = []
        for module in course.modules:
            module_lessons = []
            for lesson in module.lessons:
                lp = next((p for p in lesson_progress if p.lesson_id == lesson.id), None)
                module_lessons.append({
                    'lesson_id': lesson.id,
                    'title': lesson.title,
                    'status': lp.status if lp else 'NOT_STARTED',
                    'completion': lp.completion_percentage if lp else 0,
                    'time_spent': lp.time_spent_seconds if lp else 0
                })

            module_completion = sum(l['completion'] for l in module_lessons) / len(module_lessons) if module_lessons else 0

            modules_progress.append({
                'module_id': module.id,
                'title': module.title,
                'completion': round(module_completion, 1),
                'lessons': module_lessons
            })

        return {
            'enrolled': True,
            'course_id': course_id,
            'status': course_progress.status,
            'completion_percentage': course_progress.completion_percentage or 0,
            'progress_percentage': course_progress.completion_percentage or 0,  # Alias for frontend compatibility
            'lessons_completed': course_progress.lessons_completed or 0,
            'total_lessons': course_progress.total_lessons or 0,
            'time_spent': course_progress.total_time_spent_seconds or 0,
            'time_spent_formatted': self._format_duration(course_progress.total_time_spent_seconds or 0),
            'average_quiz_score': course_progress.average_quiz_score,
            'enrolled_at': course_progress.enrolled_at.isoformat() if course_progress.enrolled_at else None,
            'modules': modules_progress
        }

    def _format_duration(self, seconds: int) -> str:
        """Format seconds into human readable duration"""
        if not seconds:
            return "0 minutes"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes} minutes"


# Singleton instance
_progress_service = None

def get_progress_service() -> ProgressTrackingService:
    """Get the singleton progress service instance"""
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressTrackingService()
    return _progress_service
