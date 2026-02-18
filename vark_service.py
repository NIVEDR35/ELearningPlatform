from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from models import (
    db, UserInteraction, LearningStyle,
    LearningSession, VARKPrediction, EngagementEvent
)
import numpy as np
import json
import uuid

class VARKService:
    """
    Enhanced VARK Learning Style Inference Service with:
    - Session-based analysis
    - Predictive VARK using Bayesian inference
    - Behavioral fingerprinting
    - Real-time style updates
    """

    # Weights for different interaction types
    INTERACTION_WEIGHTS = {
        'VIDEO_WATCH': {'visual': 3, 'auditory': 2, 'kinesthetic': 0, 'reading_writing': 0},
        'VIDEO_COMPLETE': {'visual': 3, 'auditory': 2, 'kinesthetic': 0, 'reading_writing': 0},
        'DOCUMENT_READ': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},
        'QUIZ_ATTEMPT': {'visual': 0, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'QUIZ_COMPLETE': {'visual': 0, 'auditory': 0, 'kinesthetic': 4, 'reading_writing': 1},
        'CODING_EXERCISE': {'visual': 0, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'AUDIO_LISTEN': {'visual': 0, 'auditory': 3, 'kinesthetic': 0, 'reading_writing': 0},
        'DISCUSSION_PARTICIPATE': {'visual': 0, 'auditory': 3, 'kinesthetic': 1, 'reading_writing': 1},
        'NOTE_TAKING': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},
        'DIAGRAM_VIEW': {'visual': 3, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 0},
        'LAB_EXERCISE': {'visual': 1, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 0},
        'LESSON_COMPLETE': {'visual': 1, 'auditory': 1, 'kinesthetic': 2, 'reading_writing': 1},
        # New multi-modal content types
        'ASSIGNMENT_COMPLETE': {'visual': 0, 'auditory': 0, 'kinesthetic': 4, 'reading_writing': 2},
        'CODE_EXAMPLE_VIEW': {'visual': 2, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'INTERACTIVE_ELEMENT_USE': {'visual': 1, 'auditory': 0, 'kinesthetic': 4, 'reading_writing': 0},
        'DOCUMENT_OPEN': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 4},
    }
    
    # Resource type weights
    RESOURCE_WEIGHTS = {
        'VIDEO': {'visual': 3, 'auditory': 2, 'kinesthetic': 0, 'reading_writing': 0},
        'DOCUMENT': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},
        'QUIZ': {'visual': 0, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'ASSIGNMENT': {'visual': 0, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'AUDIO': {'visual': 0, 'auditory': 3, 'kinesthetic': 0, 'reading_writing': 0},
    }

    # Phase 2: Granular engagement signals for fine-grained VARK inference
    ENGAGEMENT_SIGNALS = {
        # Video engagement signals
        'VIDEO_REPLAY_SEGMENT': {'visual': 2, 'auditory': 2, 'kinesthetic': 0, 'reading_writing': 0},
        'VIDEO_SPEED_INCREASE': {'visual': 0, 'auditory': -1, 'kinesthetic': 1, 'reading_writing': 0},
        'VIDEO_SPEED_DECREASE': {'visual': 1, 'auditory': 2, 'kinesthetic': 0, 'reading_writing': 0},
        'VIDEO_PAUSE_LONG': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 2},
        'VIDEO_SKIP_FORWARD': {'visual': 0, 'auditory': -1, 'kinesthetic': 0, 'reading_writing': 0},
        'VIDEO_FULLSCREEN': {'visual': 2, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 0},
        'VIDEO_CAPTIONS_ENABLE': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},

        # Document engagement signals
        'DOCUMENT_HIGHLIGHT': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},
        'DOCUMENT_COPY_TEXT': {'visual': 0, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 3},
        'DOCUMENT_SCROLL_SLOW': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 2},
        'DOCUMENT_SCROLL_FAST': {'visual': 0, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': -1},
        'DOCUMENT_ZOOM_IN': {'visual': 2, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 1},

        # Code/Interactive signals
        'CODE_MODIFY': {'visual': 0, 'auditory': 0, 'kinesthetic': 4, 'reading_writing': 1},
        'CODE_RUN': {'visual': 0, 'auditory': 0, 'kinesthetic': 4, 'reading_writing': 0},
        'CODE_DEBUG': {'visual': 1, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 1},
        'CODE_COPY': {'visual': 0, 'auditory': 0, 'kinesthetic': 2, 'reading_writing': 1},

        # Note-taking signals
        'TAKE_NOTES': {'visual': 0, 'auditory': 0, 'kinesthetic': 1, 'reading_writing': 4},
        'CREATE_BOOKMARK': {'visual': 1, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 2},

        # Navigation signals
        'BACK_TO_PREVIOUS': {'visual': 1, 'auditory': 1, 'kinesthetic': 0, 'reading_writing': 1},
        'REVISIT_CONTENT': {'visual': 1, 'auditory': 1, 'kinesthetic': 1, 'reading_writing': 1},

        # Quiz/Assessment signals
        'QUIZ_RETRY': {'visual': 0, 'auditory': 0, 'kinesthetic': 3, 'reading_writing': 0},
        'CHECK_EXPLANATION': {'visual': 1, 'auditory': 1, 'kinesthetic': 0, 'reading_writing': 2},
    }

    # Bayesian prior for VARK (uniform by default)
    VARK_PRIOR = {
        'visual': 0.25,
        'auditory': 0.25,
        'kinesthetic': 0.25,
        'reading_writing': 0.25
    }

    # Exponential moving average decay factor for real-time updates
    EMA_ALPHA = 0.3  # Higher = more weight to recent events
    
    @staticmethod
    def infer_learning_style(user_id: int, min_data_points: int = 1) -> Dict:
        """Infer learning style from user interactions"""
        
        # Get user interactions
        interactions = UserInteraction.query.filter_by(user_id=user_id).all()
        
        if len(interactions) < min_data_points:
            return VARKService._create_default_style(user_id, len(interactions))
        
        # Calculate scores
        scores = VARKService._calculate_vark_scores(interactions)
        
        # Determine dominant style
        dominant_style = VARKService._determine_dominant_style(scores)
        
        # Calculate confidence
        confidence = VARKService._calculate_confidence(len(interactions), scores)
        
        # Create or update learning style
        learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
        
        if not learning_style:
            learning_style = LearningStyle(user_id=user_id)
            db.session.add(learning_style)
        
        learning_style.visual_score = scores['visual']
        learning_style.auditory_score = scores['auditory']
        learning_style.kinesthetic_score = scores['kinesthetic']
        learning_style.reading_writing_score = scores['reading_writing']
        learning_style.dominant_style = dominant_style
        learning_style.confidence = confidence
        learning_style.data_points = len(interactions)
        learning_style.last_inferred = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'visual_score': scores['visual'],
            'auditory_score': scores['auditory'],
            'kinesthetic_score': scores['kinesthetic'],
            'reading_writing_score': scores['reading_writing'],
            'dominant_style': dominant_style,
            'confidence': confidence,
            'data_points': len(interactions),
            'description': VARKService._get_style_description(dominant_style),
            'recommendations': VARKService._get_style_recommendations(dominant_style)
        }
    
    @staticmethod
    def _calculate_vark_scores(interactions: List[UserInteraction]) -> Dict[str, int]:
        """Calculate VARK scores from interactions"""
        
        scores = {'visual': 0, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 0}
        
        for interaction in interactions:
            # Get duration weight (longer interactions = more weight)
            # Safely convert duration to int
            try:
                duration = int(interaction.duration) if interaction.duration else 0
            except (ValueError, TypeError):
                duration = 0
            
            duration_weight = min(duration / 60, 10) if duration > 0 else 1
            
            # Add score based on interaction type
            if interaction.interaction_type in VARKService.INTERACTION_WEIGHTS:
                weights = VARKService.INTERACTION_WEIGHTS[interaction.interaction_type]
                for style, weight in weights.items():
                    scores[style] += weight * duration_weight
            
            # Add score based on resource type
            if interaction.resource_type in VARKService.RESOURCE_WEIGHTS:
                weights = VARKService.RESOURCE_WEIGHTS[interaction.resource_type]
                for style, weight in weights.items():
                    scores[style] += weight * duration_weight
        
        # Normalize scores to 0-100
        max_score = max(scores.values()) if max(scores.values()) > 0 else 1
        normalized_scores = {
            style: int((score / max_score) * 100)
            for style, score in scores.items()
        }
        
        return normalized_scores
    
    @staticmethod
    def _determine_dominant_style(scores: Dict[str, int]) -> str:
        """Determine dominant learning style"""
        
        max_score = max(scores.values())
        
        # Check if multiple styles have similar high scores (multimodal)
        high_score_count = sum(1 for score in scores.values() if score >= max_score - 10)
        
        if high_score_count >= 2:
            return 'MULTIMODAL'
        
        # Find the dominant style
        for style, score in scores.items():
            if score == max_score:
                return style.upper()
        
        return 'MULTIMODAL'
    
    @staticmethod
    def _calculate_confidence(data_points: int, scores: Dict[str, int]) -> float:
        """Calculate confidence based on data points and score distribution"""
        
        # Base confidence on data points
        if data_points < 20:
            base_confidence = 0.0
        elif data_points < 50:
            base_confidence = 50.0
        elif data_points < 100:
            base_confidence = 70.0
        elif data_points < 200:
            base_confidence = 85.0
        else:
            base_confidence = 95.0
        
        # Adjust based on score distribution
        # If scores are very similar, reduce confidence
        score_values = list(scores.values())
        score_std = np.std(score_values)
        
        if score_std < 10:  # Very similar scores
            base_confidence *= 0.8
        elif score_std > 30:  # Clear dominant style
            base_confidence = min(base_confidence * 1.1, 100.0)
        
        return round(base_confidence, 2)
    
    @staticmethod
    def _create_default_style(user_id: int, data_points: int) -> Dict:
        """Create default learning style for new users"""
        
        return {
            'visual_score': 50,
            'auditory_score': 50,
            'kinesthetic_score': 50,
            'reading_writing_score': 50,
            'dominant_style': 'MULTIMODAL',
            'confidence': 0.0,
            'data_points': data_points,
            'description': 'Not enough data yet. Keep using the platform to discover your learning style!',
            'recommendations': 'Try different types of content to help us understand your learning preferences.'
        }
    
    @staticmethod
    def _get_style_description(style: str) -> str:
        """Get description for learning style"""
        
        descriptions = {
            'VISUAL': 'You learn best through visual aids like diagrams, charts, videos, and images. You have strong spatial awareness and remember faces better than names.',
            'AUDITORY': 'You learn best through listening to lectures, discussions, and audio content. You enjoy verbal explanations and remember conversations well.',
            'KINESTHETIC': 'You learn best through hands-on practice, experiments, and interactive exercises. You prefer learning by doing and physical activities.',
            'READING_WRITING': 'You learn best through reading texts and writing notes. You enjoy detailed written explanations and express yourself well in writing.',
            'MULTIMODAL': 'You benefit from a variety of learning methods and adapt well to different formats. You can learn effectively through multiple modalities.'
        }
        
        return descriptions.get(style, 'Your learning style is being analyzed.')
    
    @staticmethod
    def _get_style_recommendations(style: str) -> str:
        """Get recommendations for learning style"""
        
        recommendations = {
            'VISUAL': 'Focus on video lectures, infographics, diagrams, and visual demonstrations. Use color coding and mind maps for note-taking.',
            'AUDITORY': 'Try podcasts, audio lectures, and participate in discussions. Read content aloud and explain concepts to others.',
            'KINESTHETIC': 'Engage with coding exercises, labs, and practical projects. Take breaks to move around and use hands-on learning tools.',
            'READING_WRITING': 'Take detailed notes, read documentation thoroughly, and write summaries. Create lists and organize information in written form.',
            'MULTIMODAL': 'Mix different learning methods for optimal results. Experiment with various content types to find what works best for each topic.'
        }
        
        return recommendations.get(style, 'Keep exploring different content types.')
    
    @staticmethod
    def get_content_recommendations_for_style(style: str) -> List[str]:
        """Get content type recommendations for a learning style"""
        
        content_map = {
            'VISUAL': ['VIDEO', 'DIAGRAM', 'INFOGRAPHIC', 'PRESENTATION'],
            'AUDITORY': ['AUDIO', 'PODCAST', 'DISCUSSION', 'LECTURE'],
            'KINESTHETIC': ['QUIZ', 'ASSIGNMENT', 'LAB', 'CODING_EXERCISE'],
            'READING_WRITING': ['DOCUMENT', 'ARTICLE', 'BOOK', 'NOTES'],
            'MULTIMODAL': ['VIDEO', 'DOCUMENT', 'QUIZ', 'DISCUSSION']
        }
        
        return content_map.get(style, content_map['MULTIMODAL'])
    
    @staticmethod
    def analyze_learning_pattern(user_id: int, days: int = 30) -> Dict:
        """Analyze learning patterns over time"""
        
        since = datetime.utcnow() - timedelta(days=days)
        interactions = UserInteraction.query.filter(
            UserInteraction.user_id == user_id,
            UserInteraction.timestamp >= since
        ).all()
        
        if not interactions:
            return {'message': 'No recent activity'}
        
        # Analyze by day of week
        day_distribution = {}
        hour_distribution = {}
        type_distribution = {}
        
        for interaction in interactions:
            # Day of week
            day = interaction.timestamp.strftime('%A')
            day_distribution[day] = day_distribution.get(day, 0) + 1
            
            # Hour of day
            hour = interaction.timestamp.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
            
            # Interaction type
            itype = interaction.interaction_type
            type_distribution[itype] = type_distribution.get(itype, 0) + 1
        
        # Find peak times
        peak_day = max(day_distribution, key=day_distribution.get) if day_distribution else None
        peak_hour = max(hour_distribution, key=hour_distribution.get) if hour_distribution else None
        
        return {
            'total_interactions': len(interactions),
            'day_distribution': day_distribution,
            'hour_distribution': hour_distribution,
            'type_distribution': type_distribution,
            'peak_day': peak_day,
            'peak_hour': peak_hour,
            'insights': VARKService._generate_pattern_insights(day_distribution, hour_distribution, type_distribution)
        }
    
    @staticmethod
    def _generate_pattern_insights(day_dist: Dict, hour_dist: Dict, type_dist: Dict) -> List[str]:
        """Generate insights from learning patterns"""
        
        insights = []
        
        # Day insights
        if day_dist:
            peak_day = max(day_dist, key=day_dist.get)
            insights.append(f"You're most active on {peak_day}s")
        
        # Hour insights
        if hour_dist:
            peak_hour = max(hour_dist, key=hour_dist.get)
            if 6 <= peak_hour < 12:
                insights.append("You're a morning learner")
            elif 12 <= peak_hour < 18:
                insights.append("You prefer afternoon learning sessions")
            else:
                insights.append("You're a night owl learner")
        
        # Type insights
        if type_dist:
            top_type = max(type_dist, key=type_dist.get)
            if 'VIDEO' in top_type:
                insights.append("You engage heavily with video content")
            elif 'QUIZ' in top_type or 'ASSIGNMENT' in top_type:
                insights.append("You're practice-oriented")
            elif 'DOCUMENT' in top_type:
                insights.append("You prefer reading and text-based learning")

        return insights

    # ==================== PHASE 2: ADVANCED VARK METHODS ====================

    @staticmethod
    def start_learning_session(
        user_id: int,
        device_type: str = None,
        browser: str = None,
        platform: str = None
    ) -> Dict:
        """
        Start a new learning session for behavioral tracking.

        Args:
            user_id: User ID
            device_type: Type of device (desktop, mobile, tablet)
            browser: Browser name
            platform: OS platform

        Returns:
            Session details including session_id
        """
        try:
            session_id = str(uuid.uuid4())

            session = LearningSession(
                user_id=user_id,
                session_id=session_id,
                started_at=datetime.utcnow(),
                device_type=device_type,
                browser=browser,
                platform=platform
            )

            db.session.add(session)
            db.session.commit()

            return {
                'session_id': session_id,
                'user_id': user_id,
                'started_at': session.started_at.isoformat(),
                'device_type': device_type
            }

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    @staticmethod
    def end_learning_session(session_id: str) -> Dict:
        """
        End a learning session and analyze VARK patterns.

        Args:
            session_id: Session ID to end

        Returns:
            Session analysis with VARK scores
        """
        try:
            session = LearningSession.query.filter_by(session_id=session_id).first()

            if not session:
                return {'error': 'Session not found'}

            session.ended_at = datetime.utcnow()
            session.duration_seconds = int(
                (session.ended_at - session.started_at).total_seconds()
            )

            # Get session events and analyze
            events = EngagementEvent.query.filter_by(session_id=session_id).all()

            # Calculate session VARK scores
            session_vark = VARKService._calculate_session_vark(events)
            session.session_vark_scores = json.dumps(session_vark)

            # Calculate session stats
            session.interactions_count = len(events)
            session.videos_watched = sum(1 for e in events if 'VIDEO' in e.event_type)
            session.documents_read = sum(1 for e in events if 'DOCUMENT' in e.event_type)
            session.quizzes_attempted = sum(1 for e in events if 'QUIZ' in e.event_type)

            # Calculate focus score
            session.focus_score = VARKService._calculate_focus_score(events, session.duration_seconds)

            db.session.commit()

            # Update user's overall VARK prediction
            VARKService._update_vark_prediction(session.user_id)

            return {
                'session_id': session_id,
                'duration_seconds': session.duration_seconds,
                'interactions_count': session.interactions_count,
                'session_vark_scores': session_vark,
                'focus_score': session.focus_score,
                'videos_watched': session.videos_watched,
                'documents_read': session.documents_read,
                'quizzes_attempted': session.quizzes_attempted
            }

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    @staticmethod
    def track_engagement_event(
        user_id: int,
        event_type: str,
        resource_type: str = None,
        resource_id: int = None,
        session_id: str = None,
        event_data: Dict = None,
        position: float = None,
        duration_ms: int = None
    ) -> Dict:
        """
        Track a fine-grained engagement event for VARK analysis.

        Args:
            user_id: User ID
            event_type: Type of event (from ENGAGEMENT_SIGNALS keys)
            resource_type: Type of resource (VIDEO, DOCUMENT, etc.)
            resource_id: ID of the resource
            session_id: Optional session ID
            event_data: Additional event metadata
            position: Position in content (0.0-1.0)
            duration_ms: Duration of the event in milliseconds

        Returns:
            Event tracking confirmation
        """
        try:
            # Calculate VARK signal from this event
            vark_signal = VARKService.ENGAGEMENT_SIGNALS.get(event_type, {})

            # Create engagement event
            event = EngagementEvent(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                event_data=json.dumps(event_data) if event_data else None,
                position=position,
                duration_ms=duration_ms,
                vark_signal=json.dumps(vark_signal) if vark_signal else None
            )

            # Calculate engagement signal strength
            if vark_signal:
                max_signal = max(vark_signal.values()) if vark_signal else 0
                event.engagement_signal = max_signal / 4.0  # Normalize to 0-1

            db.session.add(event)
            db.session.commit()

            # Update session if provided
            if session_id:
                session = LearningSession.query.filter_by(session_id=session_id).first()
                if session:
                    session.interactions_count = (session.interactions_count or 0) + 1
                    db.session.commit()

            return {
                'event_id': event.id,
                'event_type': event_type,
                'vark_signal': vark_signal,
                'engagement_signal': event.engagement_signal,
                'tracked_at': event.timestamp.isoformat()
            }

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    @staticmethod
    def _calculate_session_vark(events: List[EngagementEvent]) -> Dict[str, float]:
        """Calculate VARK scores for a single session"""
        scores = {'visual': 0.0, 'auditory': 0.0, 'kinesthetic': 0.0, 'reading_writing': 0.0}

        if not events:
            return scores

        for event in events:
            if event.vark_signal:
                try:
                    signal = json.loads(event.vark_signal)
                    for style, value in signal.items():
                        scores[style] += value
                except:
                    pass

        # Normalize to 0-100
        max_score = max(scores.values()) if max(scores.values()) > 0 else 1
        return {style: round((score / max_score) * 100, 1) for style, score in scores.items()}

    @staticmethod
    def _calculate_focus_score(events: List[EngagementEvent], duration_seconds: int) -> float:
        """Calculate focus score based on engagement patterns"""
        if not events or duration_seconds <= 0:
            return 0.0

        # Factors:
        # 1. Interaction density (events per minute)
        interaction_rate = (len(events) / (duration_seconds / 60))
        rate_score = min(interaction_rate / 5, 1.0) * 40  # Max 40 points

        # 2. Positive engagement signals
        positive_events = sum(
            1 for e in events
            if e.engagement_signal and e.engagement_signal > 0.5
        )
        positive_ratio = positive_events / len(events) if events else 0
        positive_score = positive_ratio * 30  # Max 30 points

        # 3. Consistency (low variance in event timing)
        if len(events) > 2:
            timestamps = [e.timestamp for e in events]
            gaps = [(timestamps[i+1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps)-1)]
            if gaps:
                gap_std = np.std(gaps) if len(gaps) > 1 else 0
                consistency_score = max(0, 30 - gap_std / 10)  # Max 30 points
            else:
                consistency_score = 15
        else:
            consistency_score = 15

        return round(rate_score + positive_score + consistency_score, 1)

    @staticmethod
    def predict_learning_style(user_id: int) -> Dict:
        """
        Predict learning style using Bayesian inference with confidence intervals.

        Returns probability distribution over VARK styles.
        """
        try:
            # Get historical sessions
            sessions = LearningSession.query.filter_by(user_id=user_id).all()

            # Get existing prediction or create new
            prediction = VARKPrediction.query.filter_by(user_id=user_id).first()

            if len(sessions) < 3:
                # Not enough data, return prior
                return {
                    'user_id': user_id,
                    'predicted_style': 'UNKNOWN',
                    'confidence': 0.0,
                    'probability_distribution': VARKService.VARK_PRIOR,
                    'message': 'Not enough sessions for prediction. Need at least 3 sessions.',
                    'sessions_analyzed': len(sessions)
                }

            # Collect session VARK scores
            session_scores = []
            for session in sessions:
                if session.session_vark_scores:
                    try:
                        scores = json.loads(session.session_vark_scores)
                        session_scores.append(scores)
                    except:
                        pass

            if not session_scores:
                return {
                    'user_id': user_id,
                    'predicted_style': 'UNKNOWN',
                    'confidence': 0.0,
                    'message': 'No valid session VARK data found'
                }

            # Calculate mean and standard deviation for each style
            style_stats = {}
            for style in ['visual', 'auditory', 'kinesthetic', 'reading_writing']:
                values = [s.get(style, 50) for s in session_scores]
                style_stats[style] = {
                    'mean': np.mean(values),
                    'std': np.std(values) if len(values) > 1 else 10.0
                }

            # Calculate Bayesian posterior
            posterior = VARKService._calculate_bayesian_posterior(style_stats)

            # Determine predicted style
            predicted_style = max(posterior, key=posterior.get).upper()

            # Calculate confidence based on posterior entropy
            entropy = -sum(p * np.log2(p + 1e-10) for p in posterior.values())
            max_entropy = np.log2(4)  # Max entropy for 4 categories
            confidence = (1 - entropy / max_entropy) * 100

            # Calculate stability (consistency over sessions)
            stability = VARKService._calculate_style_stability(session_scores)

            # Update or create prediction
            if not prediction:
                prediction = VARKPrediction(user_id=user_id)
                db.session.add(prediction)

            prediction.predicted_style = predicted_style
            prediction.prediction_confidence = confidence
            prediction.visual_mean = style_stats['visual']['mean']
            prediction.visual_std = style_stats['visual']['std']
            prediction.auditory_mean = style_stats['auditory']['mean']
            prediction.auditory_std = style_stats['auditory']['std']
            prediction.kinesthetic_mean = style_stats['kinesthetic']['mean']
            prediction.kinesthetic_std = style_stats['kinesthetic']['std']
            prediction.reading_writing_mean = style_stats['reading_writing']['mean']
            prediction.reading_writing_std = style_stats['reading_writing']['std']
            prediction.probability_distribution = json.dumps(posterior)
            prediction.data_points_used = sum(len(s) for s in session_scores)
            prediction.sessions_analyzed = len(session_scores)
            prediction.style_stability = stability
            prediction.updated_at = datetime.utcnow()

            db.session.commit()

            return {
                'user_id': user_id,
                'predicted_style': predicted_style,
                'confidence': round(confidence, 1),
                'probability_distribution': {k: round(v, 3) for k, v in posterior.items()},
                'style_statistics': {
                    style: {
                        'mean': round(stats['mean'], 1),
                        'std': round(stats['std'], 1),
                        'confidence_interval': [
                            round(max(0, stats['mean'] - 1.96 * stats['std']), 1),
                            round(min(100, stats['mean'] + 1.96 * stats['std']), 1)
                        ]
                    }
                    for style, stats in style_stats.items()
                },
                'style_stability': round(stability, 2),
                'sessions_analyzed': len(session_scores),
                'data_points_used': prediction.data_points_used
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _calculate_bayesian_posterior(style_stats: Dict) -> Dict[str, float]:
        """Calculate Bayesian posterior probability for each VARK style"""
        # Likelihood based on mean scores
        likelihoods = {}
        total = sum(stats['mean'] for stats in style_stats.values())

        for style, stats in style_stats.items():
            # Higher mean = higher likelihood
            # Penalize high variance (uncertainty)
            adjusted_score = stats['mean'] / (1 + stats['std'] / 50)
            likelihoods[style] = adjusted_score

        # Combine with prior
        posterior = {}
        for style in style_stats:
            posterior[style] = likelihoods[style] * VARKService.VARK_PRIOR[style]

        # Normalize
        total_posterior = sum(posterior.values())
        if total_posterior > 0:
            posterior = {k: v / total_posterior for k, v in posterior.items()}
        else:
            posterior = VARKService.VARK_PRIOR.copy()

        return posterior

    @staticmethod
    def _calculate_style_stability(session_scores: List[Dict]) -> float:
        """Calculate how stable/consistent the learning style is across sessions"""
        if len(session_scores) < 2:
            return 0.0

        # Find dominant style in each session
        dominant_styles = []
        for scores in session_scores:
            dominant = max(scores.items(), key=lambda x: x[1])[0]
            dominant_styles.append(dominant)

        # Calculate consistency
        from collections import Counter
        style_counts = Counter(dominant_styles)
        most_common_count = style_counts.most_common(1)[0][1]

        stability = most_common_count / len(dominant_styles)
        return stability

    @staticmethod
    def _update_vark_prediction(user_id: int):
        """Update VARK prediction after new session data"""
        # This is called automatically when a session ends
        VARKService.predict_learning_style(user_id)

    @staticmethod
    def update_vark_realtime(user_id: int, event: Dict) -> Dict:
        """
        Update VARK scores in real-time using exponential moving average.

        Args:
            user_id: User ID
            event: Event data with type and metadata

        Returns:
            Updated VARK scores
        """
        try:
            event_type = event.get('type', '')
            signal = VARKService.ENGAGEMENT_SIGNALS.get(event_type, {})

            if not signal:
                return {'message': 'Unknown event type, no update made'}

            # Get current learning style
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            if not learning_style:
                # Create new learning style
                learning_style = LearningStyle(
                    user_id=user_id,
                    visual_score=50,
                    auditory_score=50,
                    kinesthetic_score=50,
                    reading_writing_score=50,
                    dominant_style='MULTIMODAL',
                    confidence=0
                )
                db.session.add(learning_style)

            # Apply EMA update
            alpha = VARKService.EMA_ALPHA

            # Normalize signal to 0-100 scale
            max_signal = max(abs(v) for v in signal.values()) if signal.values() else 1
            normalized_signal = {k: (v / max_signal) * 50 + 50 for k, v in signal.items()}

            # Update scores with EMA
            learning_style.visual_score = int(
                alpha * normalized_signal.get('visual', 50) +
                (1 - alpha) * learning_style.visual_score
            )
            learning_style.auditory_score = int(
                alpha * normalized_signal.get('auditory', 50) +
                (1 - alpha) * learning_style.auditory_score
            )
            learning_style.kinesthetic_score = int(
                alpha * normalized_signal.get('kinesthetic', 50) +
                (1 - alpha) * learning_style.kinesthetic_score
            )
            learning_style.reading_writing_score = int(
                alpha * normalized_signal.get('reading_writing', 50) +
                (1 - alpha) * learning_style.reading_writing_score
            )

            # Recalculate dominant style
            scores = {
                'VISUAL': learning_style.visual_score,
                'AUDITORY': learning_style.auditory_score,
                'KINESTHETIC': learning_style.kinesthetic_score,
                'READING_WRITING': learning_style.reading_writing_score
            }
            learning_style.dominant_style = max(scores, key=scores.get)
            learning_style.data_points = (learning_style.data_points or 0) + 1
            learning_style.last_inferred = datetime.utcnow()

            db.session.commit()

            return {
                'user_id': user_id,
                'event_applied': event_type,
                'updated_scores': {
                    'visual': learning_style.visual_score,
                    'auditory': learning_style.auditory_score,
                    'kinesthetic': learning_style.kinesthetic_score,
                    'reading_writing': learning_style.reading_writing_score
                },
                'dominant_style': learning_style.dominant_style
            }

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    @staticmethod
    def detect_style_shift(user_id: int, window_days: int = 14) -> Dict:
        """
        Detect if user's learning style is shifting over time.

        Args:
            user_id: User ID
            window_days: Number of days to analyze

        Returns:
            Style shift analysis
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=window_days)
            midpoint = datetime.utcnow() - timedelta(days=window_days // 2)

            # Get sessions in two periods
            early_sessions = LearningSession.query.filter(
                LearningSession.user_id == user_id,
                LearningSession.started_at >= cutoff,
                LearningSession.started_at < midpoint
            ).all()

            recent_sessions = LearningSession.query.filter(
                LearningSession.user_id == user_id,
                LearningSession.started_at >= midpoint
            ).all()

            if len(early_sessions) < 2 or len(recent_sessions) < 2:
                return {
                    'user_id': user_id,
                    'shift_detected': False,
                    'message': 'Not enough data for shift detection'
                }

            # Calculate average VARK for each period
            def avg_vark(sessions):
                scores = {'visual': [], 'auditory': [], 'kinesthetic': [], 'reading_writing': []}
                for s in sessions:
                    if s.session_vark_scores:
                        try:
                            vark = json.loads(s.session_vark_scores)
                            for style in scores:
                                scores[style].append(vark.get(style, 50))
                        except:
                            pass
                return {style: np.mean(vals) if vals else 50 for style, vals in scores.items()}

            early_avg = avg_vark(early_sessions)
            recent_avg = avg_vark(recent_sessions)

            # Calculate shift magnitude
            shifts = {}
            for style in early_avg:
                shifts[style] = recent_avg[style] - early_avg[style]

            # Determine if significant shift occurred
            max_shift_style = max(shifts, key=lambda x: abs(shifts[x]))
            max_shift_magnitude = abs(shifts[max_shift_style])

            shift_detected = max_shift_magnitude > 15  # Threshold

            # Determine early and recent dominant styles
            early_dominant = max(early_avg, key=early_avg.get).upper()
            recent_dominant = max(recent_avg, key=recent_avg.get).upper()

            result = {
                'user_id': user_id,
                'analysis_period_days': window_days,
                'early_sessions': len(early_sessions),
                'recent_sessions': len(recent_sessions),
                'shift_detected': shift_detected,
                'early_dominant_style': early_dominant,
                'recent_dominant_style': recent_dominant,
                'style_changed': early_dominant != recent_dominant,
                'shifts': {style: round(shift, 1) for style, shift in shifts.items()},
                'max_shift': {
                    'style': max_shift_style,
                    'magnitude': round(max_shift_magnitude, 1),
                    'direction': 'increase' if shifts[max_shift_style] > 0 else 'decrease'
                }
            }

            if shift_detected:
                result['recommendation'] = (
                    f"Your learning style appears to be shifting towards {max_shift_style.upper()}. "
                    f"Consider exploring more {max_shift_style} content to align with this change."
                )

            return result

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def create_behavioral_fingerprint(user_id: int) -> Dict:
        """
        Create a comprehensive behavioral fingerprint for the user.

        Returns a detailed profile of learning behaviors, preferences, and patterns.
        """
        try:
            # Get all user data
            user_interactions = UserInteraction.query.filter_by(user_id=user_id).all()
            sessions = LearningSession.query.filter_by(user_id=user_id).all()
            events = EngagementEvent.query.filter_by(user_id=user_id).all()
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
            vark_prediction = VARKPrediction.query.filter_by(user_id=user_id).first()

            # Basic stats
            total_time_seconds = sum(s.duration_seconds or 0 for s in sessions)

            # VARK Profile
            vark_profile = {
                'current_style': learning_style.dominant_style if learning_style else 'UNKNOWN',
                'confidence': learning_style.confidence if learning_style else 0,
                'scores': {
                    'visual': learning_style.visual_score if learning_style else 50,
                    'auditory': learning_style.auditory_score if learning_style else 50,
                    'kinesthetic': learning_style.kinesthetic_score if learning_style else 50,
                    'reading_writing': learning_style.reading_writing_score if learning_style else 50
                }
            }

            if vark_prediction:
                vark_profile['predicted_style'] = vark_prediction.predicted_style
                vark_profile['prediction_confidence'] = vark_prediction.prediction_confidence
                vark_profile['style_stability'] = vark_prediction.style_stability

            # Temporal patterns
            if sessions:
                hour_counts = defaultdict(int)
                day_counts = defaultdict(int)
                for s in sessions:
                    hour_counts[s.started_at.hour] += 1
                    day_counts[s.started_at.strftime('%A')] += 1

                peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12
                peak_day = max(day_counts, key=day_counts.get) if day_counts else 'Monday'

                # Determine time preference
                if 6 <= peak_hour < 12:
                    time_preference = 'morning'
                elif 12 <= peak_hour < 18:
                    time_preference = 'afternoon'
                elif 18 <= peak_hour < 22:
                    time_preference = 'evening'
                else:
                    time_preference = 'night'

                temporal_patterns = {
                    'preferred_time': time_preference,
                    'peak_hour': peak_hour,
                    'peak_day': peak_day,
                    'hour_distribution': dict(hour_counts),
                    'day_distribution': dict(day_counts)
                }
            else:
                temporal_patterns = {'message': 'No session data available'}

            # Engagement profile
            if events:
                event_type_counts = defaultdict(int)
                for e in events:
                    event_type_counts[e.event_type] += 1

                # Calculate engagement characteristics
                avg_engagement = np.mean([e.engagement_signal or 0 for e in events])

                engagement_profile = {
                    'total_events': len(events),
                    'average_engagement_signal': round(avg_engagement, 2),
                    'top_event_types': dict(sorted(
                        event_type_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5])
                }
            else:
                engagement_profile = {'total_events': 0}

            # Learning velocity
            if sessions and total_time_seconds > 0:
                lessons_completed = sum(s.lessons_completed or 0 for s in sessions)
                quizzes_taken = sum(s.quizzes_attempted or 0 for s in sessions)
                avg_session_length = total_time_seconds / len(sessions)

                learning_velocity = {
                    'total_sessions': len(sessions),
                    'total_time_hours': round(total_time_seconds / 3600, 1),
                    'avg_session_minutes': round(avg_session_length / 60, 1),
                    'lessons_completed': lessons_completed,
                    'quizzes_taken': quizzes_taken,
                    'lessons_per_hour': round(lessons_completed / (total_time_seconds / 3600), 2) if total_time_seconds > 0 else 0
                }
            else:
                learning_velocity = {'message': 'Not enough data'}

            # Session preferences
            if sessions:
                durations = [s.duration_seconds or 0 for s in sessions if s.duration_seconds]
                if durations:
                    avg_duration = np.mean(durations)
                    if avg_duration < 900:  # < 15 min
                        session_style = 'micro-learner'
                    elif avg_duration < 1800:  # 15-30 min
                        session_style = 'short-session'
                    elif avg_duration < 3600:  # 30-60 min
                        session_style = 'moderate-session'
                    else:
                        session_style = 'deep-focus'

                    session_preferences = {
                        'session_style': session_style,
                        'avg_session_minutes': round(avg_duration / 60, 1),
                        'shortest_session_minutes': round(min(durations) / 60, 1),
                        'longest_session_minutes': round(max(durations) / 60, 1)
                    }
                else:
                    session_preferences = {'message': 'No duration data'}
            else:
                session_preferences = {'message': 'No sessions'}

            # Device preferences
            if sessions:
                device_counts = defaultdict(int)
                for s in sessions:
                    if s.device_type:
                        device_counts[s.device_type] += 1

                if device_counts:
                    preferred_device = max(device_counts, key=device_counts.get)
                else:
                    preferred_device = 'unknown'

                device_preferences = {
                    'preferred_device': preferred_device,
                    'device_distribution': dict(device_counts)
                }
            else:
                device_preferences = {'message': 'No device data'}

            return {
                'user_id': user_id,
                'fingerprint_generated_at': datetime.utcnow().isoformat(),
                'vark_profile': vark_profile,
                'temporal_patterns': temporal_patterns,
                'engagement_profile': engagement_profile,
                'learning_velocity': learning_velocity,
                'session_preferences': session_preferences,
                'device_preferences': device_preferences,
                'data_summary': {
                    'total_interactions': len(user_interactions),
                    'total_sessions': len(sessions),
                    'total_events': len(events),
                    'total_time_hours': round(total_time_seconds / 3600, 1) if total_time_seconds else 0
                }
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_vark_trajectory(user_id: int, days: int = 30) -> Dict:
        """
        Get VARK score evolution over time.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            VARK trajectory data for visualization
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            sessions = LearningSession.query.filter(
                LearningSession.user_id == user_id,
                LearningSession.started_at >= cutoff,
                LearningSession.session_vark_scores.isnot(None)
            ).order_by(LearningSession.started_at).all()

            if not sessions:
                return {
                    'user_id': user_id,
                    'message': 'No session data in this period',
                    'trajectory': []
                }

            trajectory = []
            for session in sessions:
                try:
                    scores = json.loads(session.session_vark_scores)
                    trajectory.append({
                        'date': session.started_at.strftime('%Y-%m-%d'),
                        'timestamp': session.started_at.isoformat(),
                        'scores': scores,
                        'dominant_style': max(scores, key=scores.get).upper()
                    })
                except:
                    pass

            # Calculate trends
            if len(trajectory) >= 2:
                first_scores = trajectory[0]['scores']
                last_scores = trajectory[-1]['scores']

                trends = {}
                for style in first_scores:
                    change = last_scores.get(style, 50) - first_scores.get(style, 50)
                    if change > 5:
                        trends[style] = 'increasing'
                    elif change < -5:
                        trends[style] = 'decreasing'
                    else:
                        trends[style] = 'stable'
            else:
                trends = {}

            return {
                'user_id': user_id,
                'period_days': days,
                'data_points': len(trajectory),
                'trajectory': trajectory,
                'trends': trends
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def analyze_session(user_id: int, session_id: str) -> Dict:
        """
        Analyze a specific learning session for VARK patterns.

        Args:
            user_id: User ID
            session_id: Session ID to analyze

        Returns:
            Detailed session analysis
        """
        try:
            session = LearningSession.query.filter_by(
                user_id=user_id,
                session_id=session_id
            ).first()

            if not session:
                return {'error': 'Session not found'}

            events = EngagementEvent.query.filter_by(session_id=session_id).all()

            # Session basic info
            duration_minutes = (session.duration_seconds or 0) / 60

            # Event breakdown
            event_breakdown = defaultdict(lambda: {'count': 0, 'total_duration_ms': 0})
            for event in events:
                event_breakdown[event.event_type]['count'] += 1
                event_breakdown[event.event_type]['total_duration_ms'] += event.duration_ms or 0

            # VARK contribution by event type
            vark_contributions = {'visual': 0, 'auditory': 0, 'kinesthetic': 0, 'reading_writing': 0}
            for event in events:
                if event.vark_signal:
                    try:
                        signal = json.loads(event.vark_signal)
                        for style, value in signal.items():
                            vark_contributions[style] += value
                    except:
                        pass

            # Session VARK scores
            session_vark = {}
            if session.session_vark_scores:
                try:
                    session_vark = json.loads(session.session_vark_scores)
                except:
                    pass

            # Determine session focus areas
            focus_areas = []
            if vark_contributions:
                sorted_contributions = sorted(
                    vark_contributions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                focus_areas = [s[0].upper() for s in sorted_contributions if s[1] > 0][:2]

            return {
                'session_id': session_id,
                'user_id': user_id,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'duration_minutes': round(duration_minutes, 1),
                'device_type': session.device_type,
                'total_interactions': session.interactions_count or 0,
                'event_breakdown': dict(event_breakdown),
                'vark_contributions': vark_contributions,
                'session_vark_scores': session_vark,
                'focus_score': session.focus_score,
                'focus_areas': focus_areas,
                'content_engaged': {
                    'videos': session.videos_watched or 0,
                    'documents': session.documents_read or 0,
                    'quizzes': session.quizzes_attempted or 0,
                    'lessons': session.lessons_completed or 0
                }
            }

        except Exception as e:
            return {'error': str(e)}

    # ==================== PHASE 2 ENHANCEMENTS ====================

    @staticmethod
    def get_dynamic_vark_weights(user_id: int) -> Dict:
        """
        Calculate dynamic VARK weights based on confidence and recency.

        Returns weights that adjust based on:
        - How confident we are in each VARK dimension
        - How recent the behavioral data is
        - Historical accuracy of predictions
        """
        try:
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
            vark_prediction = VARKPrediction.query.filter_by(user_id=user_id).first()

            # Base weights
            weights = {
                'visual': 0.25,
                'auditory': 0.25,
                'kinesthetic': 0.25,
                'reading_writing': 0.25
            }

            if not learning_style:
                return {
                    'weights': weights,
                    'confidence': 0,
                    'method': 'default_uniform'
                }

            # Calculate confidence-based weights
            scores = {
                'visual': learning_style.visual_score or 50,
                'auditory': learning_style.auditory_score or 50,
                'kinesthetic': learning_style.kinesthetic_score or 50,
                'reading_writing': learning_style.reading_writing_score or 50
            }

            total_score = sum(scores.values())
            if total_score > 0:
                # Proportional weights based on scores
                base_weights = {k: v / total_score for k, v in scores.items()}
            else:
                base_weights = weights

            # Confidence factor (0-1)
            confidence = (learning_style.confidence or 0) / 100

            # Blend uniform and proportional based on confidence
            # Low confidence = more uniform, High confidence = more differentiated
            final_weights = {}
            for style in weights:
                uniform = 0.25
                proportional = base_weights[style]
                final_weights[style] = uniform * (1 - confidence) + proportional * confidence

            # Apply recency decay if prediction exists
            recency_factor = 1.0
            if vark_prediction and vark_prediction.updated_at:
                days_old = (datetime.utcnow() - vark_prediction.updated_at).days
                # Decay factor: weight recent data more
                recency_factor = max(0.5, 1 - (days_old / 60))  # Decay over 60 days

            # Apply stability factor
            stability_factor = vark_prediction.style_stability if vark_prediction else 0.5

            return {
                'weights': final_weights,
                'confidence': confidence * 100,
                'recency_factor': recency_factor,
                'stability_factor': stability_factor,
                'data_points': learning_style.data_points or 0,
                'method': 'confidence_weighted',
                'dominant_style': learning_style.dominant_style,
                'raw_scores': scores
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_adaptive_content_recommendations(user_id: int) -> Dict:
        """
        Get content recommendations that adapt to VARK drift.

        Detects learning style changes and recommends content
        that aligns with emerging preferences.
        """
        try:
            # Get drift analysis
            drift = VARKService.detect_style_shift(user_id, window_days=14)

            # Get current profile
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            recommendations = {
                'adapt_content': False,
                'current_style': learning_style.dominant_style if learning_style else 'MULTIMODAL',
                'shift_detected': drift.get('shift_detected', False),
                'content_adjustments': [],
                'emerging_preferences': []
            }

            if drift.get('shift_detected'):
                recommendations['adapt_content'] = True

                # Identify emerging style
                shifts = drift.get('shifts', {})
                increasing_styles = [s for s, v in shifts.items() if v > 10]
                decreasing_styles = [s for s, v in shifts.items() if v < -10]

                recommendations['emerging_preferences'] = increasing_styles
                recommendations['declining_preferences'] = decreasing_styles

                # Generate content adjustments
                for style in increasing_styles:
                    if style == 'visual':
                        recommendations['content_adjustments'].append({
                            'type': 'INCREASE_VISUAL',
                            'suggestion': 'Add more video content, diagrams, and infographics',
                            'weight_boost': 1.2
                        })
                    elif style == 'auditory':
                        recommendations['content_adjustments'].append({
                            'type': 'INCREASE_AUDITORY',
                            'suggestion': 'Add more audio explanations and discussion content',
                            'weight_boost': 1.2
                        })
                    elif style == 'kinesthetic':
                        recommendations['content_adjustments'].append({
                            'type': 'INCREASE_KINESTHETIC',
                            'suggestion': 'Add more hands-on exercises and coding challenges',
                            'weight_boost': 1.2
                        })
                    elif style == 'reading_writing':
                        recommendations['content_adjustments'].append({
                            'type': 'INCREASE_READING_WRITING',
                            'suggestion': 'Add more documentation and written tutorials',
                            'weight_boost': 1.2
                        })

                # Suggestion for declining styles
                for style in decreasing_styles:
                    recommendations['content_adjustments'].append({
                        'type': f'REDUCE_{style.upper()}',
                        'suggestion': f'Consider reducing {style}-focused content',
                        'weight_reduction': 0.8
                    })

            return recommendations

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def generate_session_summary(user_id: int, session_id: str) -> Dict:
        """
        Generate comprehensive learning session summary with insights.
        """
        from models import SessionSummary, QuizAttempt

        try:
            session = LearningSession.query.filter_by(
                user_id=user_id,
                session_id=session_id
            ).first()

            if not session:
                return {'error': 'Session not found'}

            # Get all events for this session
            events = EngagementEvent.query.filter_by(session_id=session_id).all()

            # Calculate duration
            duration_minutes = 0
            if session.started_at and session.ended_at:
                duration_minutes = (session.ended_at - session.started_at).total_seconds() / 60
            elif session.duration_seconds:
                duration_minutes = session.duration_seconds / 60

            # Analyze concepts from events
            concepts_learned = []
            concepts_reinforced = []
            concepts_struggled = []

            # Get quiz attempts during session timeframe
            quiz_attempts = []
            quiz_scores = []
            if session.started_at:
                end_time = session.ended_at or datetime.utcnow()
                quiz_attempts = QuizAttempt.query.filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.started_at >= session.started_at,
                    QuizAttempt.started_at <= end_time
                ).all()

                for attempt in quiz_attempts:
                    if attempt.score is not None:
                        quiz_scores.append(attempt.score)
                    if attempt.concepts_mastered:
                        try:
                            mastered = json.loads(attempt.concepts_mastered)
                            concepts_learned.extend(mastered)
                        except:
                            pass
                    if attempt.knowledge_gaps_identified:
                        try:
                            gaps = json.loads(attempt.knowledge_gaps_identified)
                            concepts_struggled.extend(gaps)
                        except:
                            pass

            # Calculate VARK profile for session
            session_vark = VARKService._calculate_session_vark(events)
            dominant_mode = max(session_vark, key=session_vark.get) if session_vark else 'multimodal'

            # Calculate engagement score
            engagement_score = VARKService._calculate_focus_score(
                events,
                int(duration_minutes * 60)
            )

            # Calculate productivity score
            productivity_score = 0
            if duration_minutes > 0:
                outcomes = (
                    (session.lessons_completed or 0) * 20 +
                    (session.quizzes_attempted or 0) * 15 +
                    (session.videos_watched or 0) * 10
                )
                # Normalize to 0-100 based on expected outcomes per hour
                expected_per_hour = 60  # Expected outcome points per hour
                productivity_score = min(100, (outcomes / (duration_minutes / 60)) / expected_per_hour * 100)

            # Generate insights
            insights = []

            # Duration insight
            avg_session_duration = VARKService._get_user_avg_session_duration(user_id)
            if avg_session_duration > 0:
                duration_diff = ((duration_minutes - avg_session_duration) / avg_session_duration) * 100
                if duration_diff > 20:
                    insights.append(f"This session was {abs(duration_diff):.0f}% longer than your average")
                elif duration_diff < -20:
                    insights.append(f"This session was {abs(duration_diff):.0f}% shorter than your average")

            # Learning mode insight
            if session_vark.get(dominant_mode, 0) > 60:
                insights.append(f"You predominantly used {dominant_mode.upper()} learning in this session")

            # Quiz performance insight
            if quiz_scores:
                avg_quiz = sum(quiz_scores) / len(quiz_scores)
                if avg_quiz >= 80:
                    insights.append("Excellent quiz performance this session!")
                elif avg_quiz < 60:
                    insights.append("Consider reviewing the material before your next quiz attempt")

            # Engagement insight
            if engagement_score >= 75:
                insights.append("High engagement level - great focus!")
            elif engagement_score < 40:
                insights.append("Consider shorter, more focused sessions")

            # Generate recommendations
            recommendations = []

            if concepts_struggled:
                recommendations.append({
                    'type': 'REVIEW',
                    'message': f"Review these concepts: {', '.join(concepts_struggled[:3])}"
                })

            if productivity_score < 50:
                recommendations.append({
                    'type': 'FOCUS',
                    'message': "Try setting specific learning goals for your next session"
                })

            if session_vark.get(dominant_mode, 0) > 70:
                recommendations.append({
                    'type': 'DIVERSIFY',
                    'message': f"Consider trying more {VARKService._get_opposite_style(dominant_mode)} content"
                })

            # Create or update summary
            summary = SessionSummary.query.filter_by(session_id=session_id).first()
            if not summary:
                summary = SessionSummary(
                    user_id=user_id,
                    session_id=session_id,
                    started_at=session.started_at
                )
                db.session.add(summary)

            summary.ended_at = session.ended_at
            summary.duration_minutes = duration_minutes
            summary.concepts_learned = json.dumps(list(set(concepts_learned)))
            summary.concepts_reinforced = json.dumps(list(set(concepts_reinforced)))
            summary.concepts_struggled = json.dumps(list(set(concepts_struggled)))
            summary.lessons_completed = session.lessons_completed or 0
            summary.quizzes_taken = len(quiz_attempts)
            summary.quiz_avg_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else None
            summary.videos_watched = session.videos_watched or 0
            summary.session_vark_profile = json.dumps(session_vark)
            summary.dominant_learning_mode = dominant_mode.upper()
            summary.engagement_score = engagement_score
            summary.focus_score = session.focus_score
            summary.productivity_score = productivity_score
            summary.session_insights = json.dumps(insights)
            summary.recommendations = json.dumps(recommendations)

            if avg_session_duration > 0:
                summary.compared_to_avg_duration = ((duration_minutes - avg_session_duration) / avg_session_duration) * 100

            db.session.commit()

            return summary.to_dict()

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    @staticmethod
    def _get_user_avg_session_duration(user_id: int) -> float:
        """Get user's average session duration in minutes"""
        sessions = LearningSession.query.filter(
            LearningSession.user_id == user_id,
            LearningSession.duration_seconds.isnot(None)
        ).all()

        if not sessions:
            return 0

        total = sum(s.duration_seconds for s in sessions)
        return (total / len(sessions)) / 60  # Convert to minutes

    @staticmethod
    def _get_opposite_style(style: str) -> str:
        """Get the opposite learning style for diversification recommendations"""
        opposites = {
            'visual': 'reading_writing',
            'reading_writing': 'visual',
            'auditory': 'kinesthetic',
            'kinesthetic': 'auditory'
        }
        return opposites.get(style.lower(), 'multimodal')

    @staticmethod
    def analyze_learning_pattern(user_id: int, days: int = 30) -> Dict:
        """
        Analyze learning patterns over time.
        Returns insights about optimal learning times, session patterns, etc.
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            sessions = LearningSession.query.filter(
                LearningSession.user_id == user_id,
                LearningSession.started_at >= cutoff
            ).all()

            if not sessions:
                return {
                    'user_id': user_id,
                    'message': 'No session data available',
                    'patterns': {}
                }

            # Time-of-day analysis
            hour_performance = defaultdict(lambda: {'sessions': 0, 'total_focus': 0, 'total_duration': 0})
            day_performance = defaultdict(lambda: {'sessions': 0, 'total_focus': 0, 'total_duration': 0})

            for session in sessions:
                hour = session.started_at.hour
                day = session.started_at.strftime('%A')

                hour_performance[hour]['sessions'] += 1
                hour_performance[hour]['total_focus'] += session.focus_score or 0
                hour_performance[hour]['total_duration'] += session.duration_seconds or 0

                day_performance[day]['sessions'] += 1
                day_performance[day]['total_focus'] += session.focus_score or 0
                day_performance[day]['total_duration'] += session.duration_seconds or 0

            # Calculate averages and find optimal times
            best_hour = None
            best_hour_score = 0
            for hour, data in hour_performance.items():
                if data['sessions'] >= 2:  # Need at least 2 sessions
                    avg_focus = data['total_focus'] / data['sessions']
                    if avg_focus > best_hour_score:
                        best_hour_score = avg_focus
                        best_hour = hour

            best_day = None
            best_day_score = 0
            for day, data in day_performance.items():
                if data['sessions'] >= 2:
                    avg_focus = data['total_focus'] / data['sessions']
                    if avg_focus > best_day_score:
                        best_day_score = avg_focus
                        best_day = day

            # Determine time period preference
            morning_sessions = sum(1 for s in sessions if 6 <= s.started_at.hour < 12)
            afternoon_sessions = sum(1 for s in sessions if 12 <= s.started_at.hour < 18)
            evening_sessions = sum(1 for s in sessions if 18 <= s.started_at.hour < 22)
            night_sessions = sum(1 for s in sessions if s.started_at.hour >= 22 or s.started_at.hour < 6)

            time_preferences = {
                'morning': morning_sessions,
                'afternoon': afternoon_sessions,
                'evening': evening_sessions,
                'night': night_sessions
            }
            preferred_time = max(time_preferences, key=time_preferences.get)

            # Session duration analysis
            durations = [s.duration_seconds for s in sessions if s.duration_seconds]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                'user_id': user_id,
                'period_days': days,
                'total_sessions': len(sessions),
                'patterns': {
                    'optimal_hour': best_hour,
                    'optimal_hour_focus_score': round(best_hour_score, 1),
                    'optimal_day': best_day,
                    'optimal_day_focus_score': round(best_day_score, 1),
                    'preferred_time_of_day': preferred_time,
                    'time_distribution': time_preferences,
                    'avg_session_duration_minutes': round(avg_duration / 60, 1) if avg_duration else 0
                },
                'recommendations': VARKService._generate_pattern_recommendations(
                    best_hour, best_day, preferred_time, avg_duration
                )
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _generate_pattern_recommendations(
        best_hour: int,
        best_day: str,
        preferred_time: str,
        avg_duration: float
    ) -> List[str]:
        """Generate recommendations based on learning patterns"""
        recommendations = []

        if best_hour is not None:
            if 6 <= best_hour < 12:
                recommendations.append(f"You focus best in the morning around {best_hour}:00. Schedule important learning then.")
            elif 12 <= best_hour < 18:
                recommendations.append(f"Your peak focus is in the afternoon around {best_hour}:00.")
            else:
                recommendations.append(f"You're most focused in the evening around {best_hour}:00.")

        if best_day:
            recommendations.append(f"{best_day}s are your most productive learning days.")

        if avg_duration:
            avg_minutes = avg_duration / 60
            if avg_minutes < 15:
                recommendations.append("Your sessions are quite short. Try extending to 20-30 minutes for deeper learning.")
            elif avg_minutes > 90:
                recommendations.append("Consider breaking long sessions into 45-minute blocks with short breaks.")

        return recommendations
