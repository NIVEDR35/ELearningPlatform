from typing import List, Dict, Tuple, Optional
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from datetime import datetime, timedelta
from models import (
    db, User, Course, CourseRecommendation, UserInteraction, LearningStyle,
    UserCourseSequence, LatentFactors, LearningSession
)
from gemini_service import GeminiService
from vark_service import VARKService
import json
import hashlib

class RecommendationService:
    """Enhanced Hybrid Recommendation Engine with Matrix Factorization and Sequence-Awareness"""

    # Default recommendation weights
    DEFAULT_WEIGHTS = {
        'collaborative': 0.25,
        'content_based': 0.20,
        'learning_style': 0.20,
        'matrix_factorization': 0.15,
        'sequence_aware': 0.10,
        'popularity': 0.05,
        'recency': 0.05
    }

    # User behavior indicators for weight adjustment
    SOCIAL_LEARNER_INDICATORS = ['discussion', 'collaboration', 'group']
    INDEPENDENT_LEARNER_INDICATORS = ['self-paced', 'solo', 'individual']

    def __init__(self):
        self.gemini_service = GeminiService()
        self.cold_start_threshold = 5  # Minimum interactions before using ML
        self.svd_factors = 50  # Number of latent factors for SVD
        self.model_version = "v2.0"  # Current model version
    
    def get_recommendations(
        self,
        user_id: int,
        count: int = 10,
        include_reasoning: bool = True
    ) -> List[Dict]:
        """Get personalized course recommendations"""
        
        # Check if user has enough data for ML-based recommendations
        interaction_count = UserInteraction.query.filter_by(user_id=user_id).count()
        
        if interaction_count < self.cold_start_threshold:
            # Cold start: Use rule-based recommendations
            recommendations = self._rule_based_recommendations(user_id, count)
            rec_type = 'RULE_BASED'
        else:
            # Warm start: Use hybrid ML approach
            recommendations = self._hybrid_recommendations(user_id, count)
            rec_type = 'HYBRID'
        
        # Save recommendations to database
        self._save_recommendations(user_id, recommendations, rec_type)
        
        return recommendations[:count]
    
    def _rule_based_recommendations(self, user_id: int, count: int) -> List[Dict]:
        """Rule-based recommendations for new users (cold start)"""
        
        user = User.query.get(user_id)
        if not user:
            return []
        
        recommendations = []
        
        # Get all courses
        all_courses = Course.query.all()
        
        for course in all_courses:
            score = 50.0  # Base score
            reasoning = []
            
            # Rule 1: Match difficulty with user experience
            # (In real app, get user experience from profile)
            if course.difficulty == 'BEGINNER':
                score += 20
                reasoning.append("Great for beginners")
            
            # Rule 2: Popular courses
            enrollment_count = self._get_enrollment_count(course.id)
            if enrollment_count > 100:
                score += 15
                reasoning.append("Popular course")
            
            # Rule 3: Trending courses (recent enrollments)
            if self._is_trending(course.id):
                score += 10
                reasoning.append("Trending now")
            
            recommendations.append({
                'course_id': course.id,
                'course': course.to_dict(),
                'score': score,
                'reasoning': ', '.join(reasoning),
                'type': 'RULE_BASED'
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations
    
    def _hybrid_recommendations(self, user_id: int, count: int) -> List[Dict]:
        """Hybrid ML-based recommendations"""
        
        # Get recommendations from different methods
        collaborative_recs = self._collaborative_filtering(user_id, count)
        content_based_recs = self._content_based_filtering(user_id, count)
        learning_style_recs = self._learning_style_based(user_id, count)
        
        # Combine recommendations with weights
        combined = self._combine_recommendations(
            collaborative_recs,
            content_based_recs,
            learning_style_recs,
            weights={'collaborative': 0.4, 'content': 0.3, 'learning_style': 0.3}
        )
        
        # Enhance with Gemini AI
        enhanced = self._enhance_with_ai(user_id, combined)
        
        return enhanced
    
    def _collaborative_filtering(self, user_id: int, count: int) -> List[Dict]:
        """User-based collaborative filtering"""
        
        # Get all users and their course interactions
        user_course_matrix = self._build_user_course_matrix()
        
        if user_id not in user_course_matrix:
            return []
        
        # Find similar users
        similar_users = self._find_similar_users(user_id, user_course_matrix)
        
        # Get courses liked by similar users
        recommendations = []
        user_courses = set(user_course_matrix[user_id].keys())
        
        for similar_user_id, similarity in similar_users[:10]:
            for course_id, interaction_score in user_course_matrix[similar_user_id].items():
                if course_id not in user_courses:
                    course = Course.query.get(course_id)
                    if course:
                        score = similarity * interaction_score * 100
                        recommendations.append({
                            'course_id': course_id,
                            'course': course.to_dict(),
                            'score': score,
                            'reasoning': f'Users similar to you enjoyed this course',
                            'type': 'COLLABORATIVE'
                        })
        
        # Aggregate scores for same course
        course_scores = defaultdict(lambda: {'score': 0, 'count': 0, 'course': None, 'reasoning': ''})
        for rec in recommendations:
            course_scores[rec['course_id']]['score'] += rec['score']
            course_scores[rec['course_id']]['count'] += 1
            course_scores[rec['course_id']]['course'] = rec['course']
            course_scores[rec['course_id']]['reasoning'] = rec['reasoning']
        
        # Average scores
        final_recs = []
        for course_id, data in course_scores.items():
            final_recs.append({
                'course_id': course_id,
                'course': data['course'],
                'score': data['score'] / data['count'],
                'reasoning': data['reasoning'],
                'type': 'COLLABORATIVE'
            })
        
        final_recs.sort(key=lambda x: x['score'], reverse=True)
        return final_recs[:count]
    
    def _content_based_filtering(self, user_id: int, count: int) -> List[Dict]:
        """Content-based filtering using course similarity"""
        
        # Get courses user has interacted with
        user_interactions = UserInteraction.query.filter_by(
            user_id=user_id,
            resource_type='COURSE'
        ).all()
        
        if not user_interactions:
            return []
        
        user_course_ids = list(set([i.resource_id for i in user_interactions]))
        
        # Get all courses
        all_courses = Course.query.all()
        
        # Build course feature vectors
        course_vectors = {}
        for course in all_courses:
            course_vectors[course.id] = self._get_course_features(course)
        
        # Find similar courses
        recommendations = []
        for user_course_id in user_course_ids:
            if user_course_id not in course_vectors:
                continue
            
            user_course_vector = course_vectors[user_course_id]
            
            for course in all_courses:
                if course.id in user_course_ids:
                    continue  # Skip courses user already took
                
                similarity = self._calculate_course_similarity(
                    user_course_vector,
                    course_vectors[course.id]
                )
                
                if similarity > 0.3:  # Threshold
                    recommendations.append({
                        'course_id': course.id,
                        'course': course.to_dict(),
                        'score': similarity * 100,
                        'reasoning': f'Similar to courses you\'ve taken',
                        'type': 'CONTENT_BASED'
                    })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:count]
    
    def _learning_style_based(self, user_id: int, count: int) -> List[Dict]:
        """Recommendations based on learning style"""
        
        # Get user's learning style
        learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
        
        if not learning_style or learning_style.confidence < 50:
            return []
        
        # Get courses that match learning style
        all_courses = Course.query.all()
        recommendations = []
        
        for course in all_courses:
            # Calculate learning style match
            match_score = self._calculate_learning_style_match(course, learning_style)
            
            if match_score > 50:
                recommendations.append({
                    'course_id': course.id,
                    'course': course.to_dict(),
                    'score': match_score,
                    'reasoning': f'Matches your {learning_style.dominant_style} learning style',
                    'type': 'LEARNING_STYLE',
                    'learning_style_match': match_score
                })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:count]
    
    def _combine_recommendations(
        self,
        collaborative: List[Dict],
        content_based: List[Dict],
        learning_style: List[Dict],
        weights: Dict[str, float]
    ) -> List[Dict]:
        """Combine recommendations from different methods"""
        
        combined_scores = defaultdict(lambda: {
            'score': 0,
            'course': None,
            'reasoning': [],
            'learning_style_match': 0
        })
        
        # Add collaborative filtering scores
        for rec in collaborative:
            course_id = rec['course_id']
            combined_scores[course_id]['score'] += rec['score'] * weights['collaborative']
            combined_scores[course_id]['course'] = rec['course']
            combined_scores[course_id]['reasoning'].append(rec['reasoning'])
        
        # Add content-based scores
        for rec in content_based:
            course_id = rec['course_id']
            combined_scores[course_id]['score'] += rec['score'] * weights['content']
            combined_scores[course_id]['course'] = rec['course']
            combined_scores[course_id]['reasoning'].append(rec['reasoning'])
        
        # Add learning style scores
        for rec in learning_style:
            course_id = rec['course_id']
            combined_scores[course_id]['score'] += rec['score'] * weights['learning_style']
            combined_scores[course_id]['course'] = rec['course']
            combined_scores[course_id]['reasoning'].append(rec['reasoning'])
            combined_scores[course_id]['learning_style_match'] = rec.get('learning_style_match', 0)
        
        # Convert to list
        final_recommendations = []
        for course_id, data in combined_scores.items():
            final_recommendations.append({
                'course_id': course_id,
                'course': data['course'],
                'score': data['score'],
                'reasoning': ' | '.join(set(data['reasoning'])),
                'learning_style_match': data['learning_style_match'],
                'type': 'HYBRID'
            })
        
        final_recommendations.sort(key=lambda x: x['score'], reverse=True)
        return final_recommendations
    
    def _enhance_with_ai(self, user_id: int, recommendations: List[Dict]) -> List[Dict]:
        """Enhance recommendations with Gemini AI insights"""
        
        # Get user's learning style and history
        learning_style = LearningStyle.query.filter_by(user_id=user_id).first()
        
        if not learning_style:
            return recommendations
        
        # Get completed courses
        completed_courses = self._get_completed_courses(user_id)
        
        # Use Gemini to enhance reasoning
        for rec in recommendations[:5]:  # Enhance top 5
            try:
                ai_response = self.gemini_service.generate_course_recommendations(
                    learning_style.dominant_style,
                    [c['title'] for c in completed_courses],
                    "Continue learning",
                    "Intermediate"
                )
                
                # Add AI-generated insights
                if isinstance(ai_response, dict) and 'recommendations' in ai_response:
                    for ai_rec in ai_response['recommendations']:
                        if ai_rec['title'].lower() in rec['course']['title'].lower():
                            rec['reasoning'] += f" | AI Insight: {ai_rec['reasoning']}"
                            break
            except:
                pass  # Continue without AI enhancement if it fails
        
        return recommendations
    
    def _build_user_course_matrix(self) -> Dict[int, Dict[int, float]]:
        """Build user-course interaction matrix"""
        
        matrix = defaultdict(dict)
        
        interactions = UserInteraction.query.filter_by(resource_type='COURSE').all()
        
        for interaction in interactions:
            user_id = interaction.user_id
            course_id = interaction.resource_id
            
            # Calculate interaction score (based on duration and type)
            score = 1.0
            if interaction.duration:
                score = min(interaction.duration / 3600, 5.0)  # Cap at 5
            
            if course_id in matrix[user_id]:
                matrix[user_id][course_id] += score
            else:
                matrix[user_id][course_id] = score
        
        return matrix
    
    def _find_similar_users(
        self,
        user_id: int,
        user_course_matrix: Dict[int, Dict[int, float]]
    ) -> List[Tuple[int, float]]:
        """Find users similar to the given user"""
        
        if user_id not in user_course_matrix:
            return []
        
        # Get all courses
        all_courses = set()
        for courses in user_course_matrix.values():
            all_courses.update(courses.keys())
        all_courses = sorted(all_courses)
        
        # Build vectors
        user_vector = np.array([
            user_course_matrix[user_id].get(course_id, 0)
            for course_id in all_courses
        ]).reshape(1, -1)
        
        similarities = []
        for other_user_id, courses in user_course_matrix.items():
            if other_user_id == user_id:
                continue
            
            other_vector = np.array([
                courses.get(course_id, 0)
                for course_id in all_courses
            ]).reshape(1, -1)
            
            similarity = cosine_similarity(user_vector, other_vector)[0][0]
            if similarity > 0:
                similarities.append((other_user_id, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    def _get_course_features(self, course: Course) -> np.ndarray:
        """Extract features from course for similarity calculation"""
        
        # Simple feature vector: [difficulty_encoded, duration_normalized, tag_features...]
        difficulty_map = {'BEGINNER': 1, 'INTERMEDIATE': 2, 'ADVANCED': 3}
        difficulty = difficulty_map.get(course.difficulty, 2)
        
        duration = course.duration_hours / 100 if course.duration_hours else 0.5
        
        # Tag features (simple bag of words)
        tags = course.tags.split(',') if course.tags else []
        tag_features = [1 if tag.strip() in tags else 0 for tag in ['python', 'java', 'web', 'ml', 'data']]
        
        return np.array([difficulty, duration] + tag_features)
    
    def _calculate_course_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate similarity between two courses"""
        return cosine_similarity(vec1.reshape(1, -1), vec2.reshape(1, -1))[0][0]
    
    def _calculate_learning_style_match(self, course: Course, learning_style: LearningStyle) -> float:
        """Calculate how well a course matches user's learning style"""
        
        # This is simplified - in real app, courses would have metadata about content types
        # For now, use tags and description
        
        score = 50.0  # Base score
        
        tags = course.tags.lower() if course.tags else ''
        description = course.description.lower() if course.description else ''
        
        if learning_style.dominant_style == 'VISUAL':
            if 'video' in tags or 'visual' in tags or 'diagram' in description:
                score += 30
        elif learning_style.dominant_style == 'AUDITORY':
            if 'audio' in tags or 'lecture' in tags or 'discussion' in description:
                score += 30
        elif learning_style.dominant_style == 'KINESTHETIC':
            if 'hands-on' in tags or 'project' in tags or 'practice' in description:
                score += 30
        elif learning_style.dominant_style == 'READING_WRITING':
            if 'reading' in tags or 'documentation' in tags or 'text' in description:
                score += 30
        
        return min(score, 100)
    
    def _get_enrollment_count(self, course_id: int) -> int:
        """Get number of enrollments for a course"""
        return UserInteraction.query.filter_by(
            resource_type='COURSE',
            resource_id=course_id
        ).distinct(UserInteraction.user_id).count()
    
    def _is_trending(self, course_id: int, days: int = 7) -> bool:
        """Check if course is trending"""
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=days)
        
        recent_count = UserInteraction.query.filter(
            UserInteraction.resource_type == 'COURSE',
            UserInteraction.resource_id == course_id,
            UserInteraction.timestamp >= since
        ).count()
        
        return recent_count > 10
    
    def _get_completed_courses(self, user_id: int) -> List[Dict]:
        """Get courses completed by user"""
        # Simplified - in real app, track completion status
        interactions = UserInteraction.query.filter_by(
            user_id=user_id,
            resource_type='COURSE'
        ).all()
        
        course_ids = list(set([i.resource_id for i in interactions]))
        courses = Course.query.filter(Course.id.in_(course_ids)).all()
        
        return [c.to_dict() for c in courses]
    
    def _save_recommendations(self, user_id: int, recommendations: List[Dict], rec_type: str):
        """Save recommendations to database"""
        
        for rec in recommendations:
            existing = CourseRecommendation.query.filter_by(
                user_id=user_id,
                course_id=rec['course_id']
            ).first()
            
            if not existing:
                recommendation = CourseRecommendation(
                    user_id=user_id,
                    course_id=rec['course_id'],
                    recommendation_score=rec['score'],
                    recommendation_type=rec_type,
                    reasoning=rec['reasoning'],
                    learning_style_match=rec.get('learning_style_match', 0)
                )
                db.session.add(recommendation)
        
        db.session.commit()

    # ==================== PHASE 2: ENHANCED RECOMMENDATION METHODS ====================

    def get_recommendations_v2(
        self,
        user_id: int,
        count: int = 10,
        include_explanations: bool = True,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Get enhanced personalized course recommendations with all methods.

        Args:
            user_id: User ID
            count: Number of recommendations to return
            include_explanations: Whether to include AI-generated explanations
            context: Optional context (e.g., current lesson, recent activity)

        Returns:
            Dict with recommendations and metadata
        """
        interaction_count = UserInteraction.query.filter_by(user_id=user_id).count()

        if interaction_count < self.cold_start_threshold:
            recommendations = self._rule_based_recommendations(user_id, count)
            rec_type = 'RULE_BASED'
            weights_used = None
        else:
            # Get dynamically adjusted weights for this user
            weights_used = self._adjust_weights_for_user(user_id)

            # Get recommendations from all methods
            recommendations = self._hybrid_recommendations_v2(user_id, count, weights_used, context)
            rec_type = 'HYBRID_V2'

        # Save recommendations
        self._save_recommendations(user_id, recommendations, rec_type)

        # Build response
        result = {
            'user_id': user_id,
            'recommendation_type': rec_type,
            'weights_used': weights_used,
            'total_recommendations': len(recommendations),
            'recommendations': recommendations[:count]
        }

        if include_explanations and recommendations:
            result['ai_explanations'] = self._generate_ai_explanations(
                user_id, recommendations[:min(5, count)]
            )

        return result

    def _hybrid_recommendations_v2(
        self,
        user_id: int,
        count: int,
        weights: Dict[str, float],
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """Enhanced hybrid recommendations with all methods"""

        # Gather recommendations from all sources
        collaborative_recs = self._collaborative_filtering(user_id, count * 2)
        content_based_recs = self._content_based_filtering(user_id, count * 2)
        learning_style_recs = self._learning_style_based(user_id, count * 2)
        mf_recs = self._matrix_factorization_recommendations(user_id, count * 2)
        sequence_recs = self._sequence_aware_recommendations(user_id, count * 2)
        popularity_recs = self._popularity_based_recommendations(count * 2)
        recency_recs = self._recency_based_recommendations(count * 2)

        # Combine all recommendations with weights
        combined = self._combine_recommendations_v2(
            user_id,
            {
                'collaborative': collaborative_recs,
                'content_based': content_based_recs,
                'learning_style': learning_style_recs,
                'matrix_factorization': mf_recs,
                'sequence_aware': sequence_recs,
                'popularity': popularity_recs,
                'recency': recency_recs
            },
            weights
        )

        # Apply context-based boosting if context provided
        if context:
            combined = self._apply_context_boost(combined, context)

        # Enhance with AI
        enhanced = self._enhance_with_ai(user_id, combined)

        return enhanced

    def _adjust_weights_for_user(self, user_id: int) -> Dict[str, float]:
        """
        Dynamically adjust recommendation weights based on user behavior.
        """
        weights = self.DEFAULT_WEIGHTS.copy()

        try:
            user = User.query.get(user_id)
            if not user:
                return weights

            # Get user's learning style
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            # Get user's interaction patterns
            interactions = UserInteraction.query.filter_by(user_id=user_id).all()

            # Adjustment 1: Strong VARK preference
            if learning_style and learning_style.confidence >= 70:
                weights['learning_style'] = 0.30
                weights['collaborative'] = 0.20

            # Adjustment 2: Social vs Independent learner
            social_score = 0
            for interaction in interactions:
                if interaction.metadata:
                    try:
                        meta = json.loads(interaction.metadata) if isinstance(interaction.metadata, str) else interaction.metadata
                        interaction_type = meta.get('type', '')
                        if any(indicator in interaction_type.lower() for indicator in self.SOCIAL_LEARNER_INDICATORS):
                            social_score += 1
                    except:
                        pass

            if social_score > len(interactions) * 0.3:
                # Social learner: boost collaborative
                weights['collaborative'] = 0.35
                weights['content_based'] = 0.15

            # Adjustment 3: Sequence follower (completes courses in order)
            sequences = UserCourseSequence.query.filter_by(user_id=user_id).count()
            if sequences >= 3:
                # User follows learning sequences
                weights['sequence_aware'] = 0.20
                weights['popularity'] = 0.03

            # Adjustment 4: New user (fewer interactions)
            if len(interactions) < 15:
                # Rely more on popularity and content-based
                weights['popularity'] = 0.15
                weights['matrix_factorization'] = 0.10

            # Normalize weights to sum to 1.0
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}

        except Exception as e:
            print(f"Error adjusting weights: {str(e)}")

        return weights

    def _matrix_factorization_recommendations(
        self,
        user_id: int,
        count: int
    ) -> List[Dict]:
        """
        Get recommendations using SVD-based matrix factorization.
        """
        try:
            # Check for cached latent factors
            user_factors = LatentFactors.query.filter_by(
                entity_type='USER',
                entity_id=user_id,
                model_version=self.model_version
            ).first()

            if not user_factors:
                # Compute factors if not cached
                self._compute_latent_factors()
                user_factors = LatentFactors.query.filter_by(
                    entity_type='USER',
                    entity_id=user_id,
                    model_version=self.model_version
                ).first()

            if not user_factors:
                return []

            # Get all course factors
            course_factors_records = LatentFactors.query.filter_by(
                entity_type='COURSE',
                model_version=self.model_version
            ).all()

            if not course_factors_records:
                return []

            # Parse user factors
            user_vector = np.array(json.loads(user_factors.factors))

            # Calculate predicted ratings for all courses
            predictions = []
            user_courses = self._get_user_course_ids(user_id)

            for cf in course_factors_records:
                if cf.entity_id in user_courses:
                    continue  # Skip already taken courses

                course_vector = np.array(json.loads(cf.factors))
                predicted_rating = np.dot(user_vector, course_vector)

                course = Course.query.get(cf.entity_id)
                if course:
                    predictions.append({
                        'course_id': cf.entity_id,
                        'course': course.to_dict(),
                        'score': float(predicted_rating) * 20,  # Scale to 0-100
                        'reasoning': 'Predicted high match based on similar user patterns',
                        'type': 'MATRIX_FACTORIZATION'
                    })

            predictions.sort(key=lambda x: x['score'], reverse=True)
            return predictions[:count]

        except Exception as e:
            print(f"Error in matrix factorization: {str(e)}")
            return []

    def _compute_latent_factors(self):
        """Compute and store SVD latent factors for users and courses"""
        try:
            # Build user-course interaction matrix
            interactions = UserInteraction.query.filter_by(resource_type='COURSE').all()

            if not interactions:
                return

            # Get unique users and courses
            user_ids = sorted(set(i.user_id for i in interactions))
            course_ids = sorted(set(i.resource_id for i in interactions))

            if len(user_ids) < 2 or len(course_ids) < 2:
                return

            user_idx = {uid: idx for idx, uid in enumerate(user_ids)}
            course_idx = {cid: idx for idx, cid in enumerate(course_ids)}

            # Build sparse matrix
            rows, cols, data = [], [], []
            for interaction in interactions:
                rows.append(user_idx[interaction.user_id])
                cols.append(course_idx[interaction.resource_id])
                # Calculate interaction strength
                score = 1.0
                if interaction.duration:
                    score = min(interaction.duration / 3600, 5.0)
                data.append(score)

            matrix = csr_matrix(
                (data, (rows, cols)),
                shape=(len(user_ids), len(course_ids))
            )

            # Compute SVD
            k = min(self.svd_factors, min(matrix.shape) - 1)
            if k < 1:
                return

            U, sigma, Vt = svds(matrix.astype(float), k=k)

            # Store user factors
            for uid, idx in user_idx.items():
                user_vector = U[idx] * sigma  # Incorporate singular values

                existing = LatentFactors.query.filter_by(
                    entity_type='USER',
                    entity_id=uid,
                    model_version=self.model_version
                ).first()

                if existing:
                    existing.factors = json.dumps(user_vector.tolist())
                    existing.computed_at = datetime.utcnow()
                else:
                    new_factor = LatentFactors(
                        entity_type='USER',
                        entity_id=uid,
                        factors=json.dumps(user_vector.tolist()),
                        num_factors=k,
                        model_version=self.model_version
                    )
                    db.session.add(new_factor)

            # Store course factors
            for cid, idx in course_idx.items():
                course_vector = Vt.T[idx]

                existing = LatentFactors.query.filter_by(
                    entity_type='COURSE',
                    entity_id=cid,
                    model_version=self.model_version
                ).first()

                if existing:
                    existing.factors = json.dumps(course_vector.tolist())
                    existing.computed_at = datetime.utcnow()
                else:
                    new_factor = LatentFactors(
                        entity_type='COURSE',
                        entity_id=cid,
                        factors=json.dumps(course_vector.tolist()),
                        num_factors=k,
                        model_version=self.model_version
                    )
                    db.session.add(new_factor)

            db.session.commit()

        except Exception as e:
            print(f"Error computing latent factors: {str(e)}")
            db.session.rollback()

    def _sequence_aware_recommendations(
        self,
        user_id: int,
        count: int
    ) -> List[Dict]:
        """
        Recommend based on similar users' learning sequences.
        Find users who took similar course sequences and recommend what they took next.
        """
        try:
            # Get user's course sequence
            user_sequences = UserCourseSequence.query.filter_by(
                user_id=user_id
            ).order_by(UserCourseSequence.sequence_position).all()

            if len(user_sequences) < 2:
                return []

            user_course_order = [s.course_id for s in user_sequences]
            user_course_set = set(user_course_order)

            # Find similar learning paths from other users
            all_sequences = UserCourseSequence.query.filter(
                UserCourseSequence.user_id != user_id
            ).all()

            # Group by user
            user_paths = defaultdict(list)
            for seq in all_sequences:
                user_paths[seq.user_id].append((seq.sequence_position, seq.course_id))

            # Sort each user's path by position
            for uid in user_paths:
                user_paths[uid] = [cid for _, cid in sorted(user_paths[uid])]

            # Find similar paths and what comes next
            recommendations = []
            for other_user_id, other_path in user_paths.items():
                if len(other_path) <= len(user_course_order):
                    continue

                # Calculate sequence similarity (Jaccard + order bonus)
                other_set = set(other_path[:len(user_course_order)])
                intersection = len(user_course_set & other_set)
                union = len(user_course_set | other_set)

                if union == 0:
                    continue

                jaccard = intersection / union

                # Order similarity bonus
                order_matches = sum(
                    1 for i, cid in enumerate(user_course_order)
                    if i < len(other_path) and other_path[i] == cid
                )
                order_bonus = order_matches / len(user_course_order) * 0.3

                similarity = jaccard + order_bonus

                if similarity > 0.3:
                    # Recommend courses this user took after the common sequence
                    for i, course_id in enumerate(other_path):
                        if course_id not in user_course_set:
                            course = Course.query.get(course_id)
                            if course:
                                # Get sequence info
                                seq_info = next(
                                    (s for s in all_sequences
                                     if s.user_id == other_user_id and s.course_id == course_id),
                                    None
                                )
                                score_bonus = 0
                                if seq_info:
                                    if seq_info.final_quiz_score and seq_info.final_quiz_score > 80:
                                        score_bonus = 10
                                    if seq_info.engagement_score and seq_info.engagement_score > 70:
                                        score_bonus += 5

                                recommendations.append({
                                    'course_id': course_id,
                                    'course': course.to_dict(),
                                    'score': (similarity * 80) + score_bonus,
                                    'reasoning': f'Learners with similar paths took this next',
                                    'type': 'SEQUENCE_AWARE',
                                    'sequence_position': i + 1
                                })

            # Aggregate by course
            course_scores = defaultdict(lambda: {'score': 0, 'count': 0, 'course': None, 'reasoning': ''})
            for rec in recommendations:
                cid = rec['course_id']
                course_scores[cid]['score'] += rec['score']
                course_scores[cid]['count'] += 1
                course_scores[cid]['course'] = rec['course']
                course_scores[cid]['reasoning'] = rec['reasoning']

            final_recs = []
            for course_id, data in course_scores.items():
                final_recs.append({
                    'course_id': course_id,
                    'course': data['course'],
                    'score': data['score'] / data['count'],
                    'reasoning': data['reasoning'],
                    'type': 'SEQUENCE_AWARE'
                })

            final_recs.sort(key=lambda x: x['score'], reverse=True)
            return final_recs[:count]

        except Exception as e:
            print(f"Error in sequence-aware recommendations: {str(e)}")
            return []

    def _popularity_based_recommendations(self, count: int) -> List[Dict]:
        """Get recommendations based on overall popularity"""
        try:
            from sqlalchemy import func

            # Get course enrollment counts
            enrollment_counts = db.session.query(
                UserInteraction.resource_id,
                func.count(func.distinct(UserInteraction.user_id)).label('count')
            ).filter(
                UserInteraction.resource_type == 'COURSE'
            ).group_by(
                UserInteraction.resource_id
            ).order_by(
                func.count(func.distinct(UserInteraction.user_id)).desc()
            ).limit(count).all()

            recommendations = []
            for course_id, enrollment_count in enrollment_counts:
                course = Course.query.get(course_id)
                if course:
                    recommendations.append({
                        'course_id': course_id,
                        'course': course.to_dict(),
                        'score': min(enrollment_count * 5, 100),
                        'reasoning': f'Popular course with {enrollment_count} learners',
                        'type': 'POPULARITY'
                    })

            return recommendations

        except Exception as e:
            print(f"Error in popularity recommendations: {str(e)}")
            return []

    def _recency_based_recommendations(self, count: int, days: int = 30) -> List[Dict]:
        """Get recommendations based on recent activity/additions"""
        try:
            from sqlalchemy import func

            cutoff = datetime.utcnow() - timedelta(days=days)

            # Get recently popular courses
            recent_enrollments = db.session.query(
                UserInteraction.resource_id,
                func.count(func.distinct(UserInteraction.user_id)).label('count')
            ).filter(
                UserInteraction.resource_type == 'COURSE',
                UserInteraction.timestamp >= cutoff
            ).group_by(
                UserInteraction.resource_id
            ).order_by(
                func.count(func.distinct(UserInteraction.user_id)).desc()
            ).limit(count).all()

            recommendations = []
            for course_id, recent_count in recent_enrollments:
                course = Course.query.get(course_id)
                if course:
                    recommendations.append({
                        'course_id': course_id,
                        'course': course.to_dict(),
                        'score': min(recent_count * 8, 100),
                        'reasoning': f'Trending: {recent_count} recent enrollments',
                        'type': 'RECENCY'
                    })

            return recommendations

        except Exception as e:
            print(f"Error in recency recommendations: {str(e)}")
            return []

    def _combine_recommendations_v2(
        self,
        user_id: int,
        all_recs: Dict[str, List[Dict]],
        weights: Dict[str, float]
    ) -> List[Dict]:
        """Combine recommendations from all methods with weighted scoring"""

        combined_scores = defaultdict(lambda: {
            'score': 0,
            'course': None,
            'reasoning': [],
            'sources': [],
            'learning_style_match': 0
        })

        # Get user's enrolled courses to exclude
        user_courses = self._get_user_course_ids(user_id)

        for method, recs in all_recs.items():
            weight = weights.get(method, 0.1)

            for rec in recs:
                course_id = rec['course_id']

                # Skip if already enrolled
                if course_id in user_courses:
                    continue

                combined_scores[course_id]['score'] += rec['score'] * weight
                combined_scores[course_id]['course'] = rec['course']
                combined_scores[course_id]['reasoning'].append(rec['reasoning'])
                combined_scores[course_id]['sources'].append(method)

                if rec.get('learning_style_match'):
                    combined_scores[course_id]['learning_style_match'] = max(
                        combined_scores[course_id]['learning_style_match'],
                        rec['learning_style_match']
                    )

        # Convert to list
        final_recommendations = []
        for course_id, data in combined_scores.items():
            if data['course']:
                final_recommendations.append({
                    'course_id': course_id,
                    'course': data['course'],
                    'score': data['score'],
                    'reasoning': ' | '.join(set(data['reasoning'])),
                    'sources': list(set(data['sources'])),
                    'learning_style_match': data['learning_style_match'],
                    'type': 'HYBRID_V2'
                })

        final_recommendations.sort(key=lambda x: x['score'], reverse=True)
        return final_recommendations

    def _apply_context_boost(
        self,
        recommendations: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """Apply context-based boosting to recommendations"""

        current_topic = context.get('current_topic', '')
        current_difficulty = context.get('current_difficulty', '')
        time_of_day = context.get('time_of_day', '')  # morning, afternoon, evening

        for rec in recommendations:
            boost = 0
            course = rec['course']

            # Topic continuity boost
            if current_topic and course.get('title'):
                if current_topic.lower() in course['title'].lower():
                    boost += 15
                    rec['reasoning'] += ' | Continues your current topic'

            # Difficulty progression boost
            if current_difficulty:
                course_diff = course.get('difficulty', '')
                difficulty_order = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED']

                try:
                    current_idx = difficulty_order.index(current_difficulty.upper())
                    course_idx = difficulty_order.index(course_diff.upper())

                    if course_idx == current_idx + 1:
                        boost += 10
                        rec['reasoning'] += ' | Next difficulty level'
                    elif course_idx == current_idx:
                        boost += 5
                except ValueError:
                    pass

            # Time-based boost (shorter courses in evening, etc.)
            if time_of_day and course.get('duration_hours'):
                duration = course['duration_hours']
                if time_of_day == 'evening' and duration <= 2:
                    boost += 5
                elif time_of_day == 'morning' and duration >= 5:
                    boost += 5

            rec['score'] += boost

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations

    def _get_user_course_ids(self, user_id: int) -> set:
        """Get set of course IDs user has interacted with"""
        interactions = UserInteraction.query.filter_by(
            user_id=user_id,
            resource_type='COURSE'
        ).all()
        return set(i.resource_id for i in interactions)

    def _generate_ai_explanations(
        self,
        user_id: int,
        recommendations: List[Dict]
    ) -> List[Dict]:
        """Generate AI-powered explanations for top recommendations"""
        explanations = []

        try:
            user = User.query.get(user_id)
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            style_name = learning_style.dominant_style if learning_style else 'general'

            for rec in recommendations:
                course = rec['course']

                prompt = f"""
                Explain in 1-2 sentences why "{course.get('title', 'this course')}"
                is recommended for a {style_name} learner.
                Focus on how the course content matches their learning preferences.
                """

                try:
                    response = self.gemini_service.generate_content(prompt)
                    explanations.append({
                        'course_id': rec['course_id'],
                        'explanation': response if isinstance(response, str) else str(response)
                    })
                except:
                    explanations.append({
                        'course_id': rec['course_id'],
                        'explanation': rec['reasoning']
                    })

        except Exception as e:
            print(f"Error generating AI explanations: {str(e)}")

        return explanations

    def update_recommendations_realtime(
        self,
        user_id: int,
        trigger_event: Dict
    ) -> Dict:
        """
        Update recommendations in real-time based on user actions.

        Args:
            user_id: User ID
            trigger_event: Event that triggered the update
                - type: 'COURSE_COMPLETE', 'COURSE_ENROLL', 'LESSON_COMPLETE', 'QUIZ_COMPLETE'
                - resource_id: ID of the related resource
                - score: Optional score (for quizzes)
                - metadata: Additional event data

        Returns:
            Updated recommendations
        """
        event_type = trigger_event.get('type', '')
        resource_id = trigger_event.get('resource_id')

        # Record the sequence for sequence-aware recommendations
        if event_type == 'COURSE_COMPLETE' and resource_id:
            self._record_course_sequence(user_id, resource_id, trigger_event)

        # Invalidate cached recommendations
        self._invalidate_user_recommendations(user_id)

        # Get fresh recommendations
        new_recs = self.get_recommendations_v2(
            user_id,
            count=10,
            include_explanations=False
        )

        return {
            'trigger': trigger_event,
            'updated_at': datetime.utcnow().isoformat(),
            'recommendations': new_recs
        }

    def _record_course_sequence(
        self,
        user_id: int,
        course_id: int,
        event_data: Dict
    ):
        """Record course completion in user's learning sequence"""
        try:
            # Get current sequence position
            last_sequence = UserCourseSequence.query.filter_by(
                user_id=user_id
            ).order_by(UserCourseSequence.sequence_position.desc()).first()

            position = (last_sequence.sequence_position + 1) if last_sequence else 1

            # Create sequence record
            sequence = UserCourseSequence(
                user_id=user_id,
                course_id=course_id,
                sequence_position=position,
                final_quiz_score=event_data.get('score'),
                engagement_score=event_data.get('engagement_score'),
                completed_at=datetime.utcnow()
            )

            db.session.add(sequence)
            db.session.commit()

        except Exception as e:
            print(f"Error recording course sequence: {str(e)}")
            db.session.rollback()

    def _invalidate_user_recommendations(self, user_id: int):
        """Invalidate cached recommendations for a user"""
        try:
            # Delete old recommendations
            CourseRecommendation.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        except Exception as e:
            print(f"Error invalidating recommendations: {str(e)}")
            db.session.rollback()

    def retrain_matrix_factorization(self) -> Dict:
        """
        Retrain the matrix factorization model.
        Should be called periodically (e.g., daily) or after significant data changes.
        """
        try:
            # Clear old factors
            LatentFactors.query.filter_by(model_version=self.model_version).delete()
            db.session.commit()

            # Compute new factors
            self._compute_latent_factors()

            # Get stats
            user_count = LatentFactors.query.filter_by(
                entity_type='USER',
                model_version=self.model_version
            ).count()

            course_count = LatentFactors.query.filter_by(
                entity_type='COURSE',
                model_version=self.model_version
            ).count()

            return {
                'status': 'success',
                'model_version': self.model_version,
                'users_processed': user_count,
                'courses_processed': course_count,
                'trained_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_recommendation_explanation(
        self,
        user_id: int,
        course_id: int
    ) -> Dict:
        """
        Get detailed AI-generated explanation for why a course is recommended.
        """
        try:
            user = User.query.get(user_id)
            course = Course.query.get(course_id)
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            if not course:
                return {'error': 'Course not found'}

            # Get recommendation record
            rec = CourseRecommendation.query.filter_by(
                user_id=user_id,
                course_id=course_id
            ).first()

            # Build context for AI explanation
            context = {
                'course_title': course.title,
                'course_description': course.description,
                'course_difficulty': course.difficulty,
                'learning_style': learning_style.dominant_style if learning_style else 'not assessed',
                'recommendation_score': rec.recommendation_score if rec else 0,
                'recommendation_type': rec.recommendation_type if rec else 'N/A'
            }

            # Get completed courses for context
            completed = self._get_completed_courses(user_id)
            context['completed_courses'] = [c['title'] for c in completed[:5]]

            prompt = f"""
            Explain why the course "{context['course_title']}" is recommended for this learner:

            - Learning Style: {context['learning_style']}
            - Previously completed: {', '.join(context['completed_courses']) if context['completed_courses'] else 'None yet'}
            - Course difficulty: {context['course_difficulty']}

            Provide a detailed but concise explanation (3-4 sentences) covering:
            1. How this course fits their learning journey
            2. Why it matches their learning style
            3. What they'll gain from taking this course
            """

            explanation = self.gemini_service.generate_content(prompt)

            return {
                'course_id': course_id,
                'course_title': course.title,
                'recommendation_score': context['recommendation_score'],
                'recommendation_type': context['recommendation_type'],
                'learning_style': context['learning_style'],
                'ai_explanation': explanation if isinstance(explanation, str) else str(explanation),
                'completed_courses_considered': context['completed_courses']
            }

        except Exception as e:
            return {'error': str(e)}

    # ==================== BIAS-AWARE CONTENT SELECTION ====================

    def analyze_content_bias(self, user_id: int) -> Dict:
        """
        Analyze content exposure bias for a user.

        Identifies imbalances in:
        - Content types (video, text, interactive)
        - Difficulty levels
        - Topics
        - Sources/Instructors
        """
        from models import ContentBias, LearningStyle
        from sqlalchemy import func

        try:
            # Get all user interactions
            interactions = UserInteraction.query.filter_by(user_id=user_id).all()

            if not interactions:
                return {
                    'user_id': user_id,
                    'message': 'No interaction data available',
                    'bias_analysis': {}
                }

            # Content type distribution
            type_counts = defaultdict(int)
            difficulty_counts = defaultdict(int)
            topic_counts = defaultdict(int)
            source_counts = defaultdict(int)

            for interaction in interactions:
                # Count resource types
                type_counts[interaction.resource_type or 'UNKNOWN'] += 1

                # Get course info for difficulty and topic
                if interaction.resource_type == 'COURSE' and interaction.resource_id:
                    course = Course.query.get(interaction.resource_id)
                    if course:
                        difficulty_counts[course.difficulty or 'UNKNOWN'] += 1
                        if course.tags:
                            for tag in course.tags.split(','):
                                topic_counts[tag.strip()] += 1

            total_interactions = len(interactions)

            # Calculate percentages
            content_distribution = {
                'video': type_counts.get('VIDEO', 0) / total_interactions * 100,
                'document': type_counts.get('DOCUMENT', 0) / total_interactions * 100,
                'interactive': (type_counts.get('QUIZ', 0) + type_counts.get('ASSIGNMENT', 0)) / total_interactions * 100,
                'course': type_counts.get('COURSE', 0) / total_interactions * 100
            }

            difficulty_distribution = {
                'beginner': difficulty_counts.get('BEGINNER', 0) / total_interactions * 100 if total_interactions else 0,
                'intermediate': difficulty_counts.get('INTERMEDIATE', 0) / total_interactions * 100 if total_interactions else 0,
                'advanced': difficulty_counts.get('ADVANCED', 0) / total_interactions * 100 if total_interactions else 0
            }

            # Calculate topic diversity (Shannon entropy)
            topic_total = sum(topic_counts.values()) if topic_counts else 1
            topic_diversity = 0
            for count in topic_counts.values():
                if count > 0:
                    p = count / topic_total
                    topic_diversity -= p * np.log2(p + 1e-10)
            # Normalize to 0-100
            max_entropy = np.log2(max(len(topic_counts), 1))
            topic_diversity_score = (topic_diversity / max_entropy * 100) if max_entropy > 0 else 0

            # Get user's learning style for VARK alignment check
            learning_style = LearningStyle.query.filter_by(user_id=user_id).first()

            # Calculate VARK content alignment
            vark_alignment = 50  # Default neutral
            if learning_style:
                dominant = learning_style.dominant_style
                if dominant == 'VISUAL':
                    vark_alignment = content_distribution['video']
                elif dominant == 'READING_WRITING':
                    vark_alignment = content_distribution['document']
                elif dominant == 'KINESTHETIC':
                    vark_alignment = content_distribution['interactive']

            # Identify underexposed content types
            ideal_distribution = {'video': 30, 'document': 25, 'interactive': 30, 'course': 15}
            underexposed_types = [
                ctype for ctype, ideal in ideal_distribution.items()
                if content_distribution.get(ctype, 0) < ideal * 0.5  # Less than half of ideal
            ]

            # Identify underexposed topics (topics with less than 5% exposure)
            underexposed_topics = [
                topic for topic, count in topic_counts.items()
                if count / topic_total < 0.05
            ]

            # Calculate difficulty appropriateness based on user skill
            user_skill = 50  # Default
            if learning_style:
                from models import LearningBehavior
                behavior = LearningBehavior.query.filter_by(user_id=user_id).first()
                if behavior and behavior.average_quiz_score:
                    user_skill = behavior.average_quiz_score

            ideal_difficulty = 'INTERMEDIATE'
            if user_skill >= 75:
                ideal_difficulty = 'ADVANCED'
            elif user_skill < 50:
                ideal_difficulty = 'BEGINNER'

            difficulty_appropriateness = difficulty_distribution.get(ideal_difficulty.lower(), 0)

            # Create or update ContentBias record
            bias_record = ContentBias.query.filter_by(user_id=user_id).first()
            if not bias_record:
                bias_record = ContentBias(user_id=user_id)
                db.session.add(bias_record)

            bias_record.video_exposure_pct = content_distribution['video']
            bias_record.document_exposure_pct = content_distribution['document']
            bias_record.interactive_exposure_pct = content_distribution['interactive']
            bias_record.beginner_content_pct = difficulty_distribution['beginner']
            bias_record.intermediate_content_pct = difficulty_distribution['intermediate']
            bias_record.advanced_content_pct = difficulty_distribution['advanced']
            bias_record.topic_distribution = json.dumps(dict(topic_counts))
            bias_record.topic_diversity_score = topic_diversity_score
            bias_record.vark_content_alignment = vark_alignment
            bias_record.difficulty_appropriateness = difficulty_appropriateness
            bias_record.underexposed_types = json.dumps(underexposed_types)
            bias_record.underexposed_topics = json.dumps(underexposed_topics[:10])
            bias_record.last_calculated = datetime.utcnow()

            db.session.commit()

            return {
                'user_id': user_id,
                'total_interactions': total_interactions,
                'content_distribution': content_distribution,
                'difficulty_distribution': difficulty_distribution,
                'topic_distribution': dict(topic_counts),
                'topic_diversity_score': round(topic_diversity_score, 1),
                'vark_content_alignment': round(vark_alignment, 1),
                'difficulty_appropriateness': round(difficulty_appropriateness, 1),
                'bias_indicators': {
                    'underexposed_content_types': underexposed_types,
                    'underexposed_topics': underexposed_topics[:5],
                    'needs_more_variety': topic_diversity_score < 50,
                    'content_style_mismatch': vark_alignment < 30
                },
                'recommendations': self._generate_bias_recommendations(
                    content_distribution, underexposed_types, vark_alignment,
                    learning_style.dominant_style if learning_style else None,
                    difficulty_appropriateness, ideal_difficulty
                )
            }

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def _generate_bias_recommendations(
        self,
        content_dist: Dict,
        underexposed: List,
        vark_alignment: float,
        dominant_style: str,
        diff_appropriateness: float,
        ideal_difficulty: str
    ) -> List[Dict]:
        """Generate recommendations to balance content bias"""
        recommendations = []

        # Content type recommendations
        if 'video' in underexposed:
            recommendations.append({
                'type': 'CONTENT_TYPE',
                'priority': 'MEDIUM',
                'message': 'Try incorporating more video content into your learning',
                'action': 'Search for video tutorials on your current topics'
            })

        if 'interactive' in underexposed:
            recommendations.append({
                'type': 'CONTENT_TYPE',
                'priority': 'HIGH',
                'message': 'Practice more with quizzes and hands-on exercises',
                'action': 'Take more quizzes to reinforce learning'
            })

        if 'document' in underexposed:
            recommendations.append({
                'type': 'CONTENT_TYPE',
                'priority': 'MEDIUM',
                'message': 'Reading documentation can deepen understanding',
                'action': 'Explore written tutorials and documentation'
            })

        # VARK alignment
        if vark_alignment < 30 and dominant_style:
            style_content = {
                'VISUAL': 'video content and diagrams',
                'AUDITORY': 'audio lectures and discussions',
                'KINESTHETIC': 'hands-on projects and coding exercises',
                'READING_WRITING': 'written tutorials and documentation'
            }
            recommendations.append({
                'type': 'VARK_ALIGNMENT',
                'priority': 'HIGH',
                'message': f"Your content doesn't align well with your {dominant_style} learning style",
                'action': f"Seek out more {style_content.get(dominant_style, 'varied content')}"
            })

        # Difficulty appropriateness
        if diff_appropriateness < 30:
            recommendations.append({
                'type': 'DIFFICULTY',
                'priority': 'MEDIUM',
                'message': f"Most of your content may not match your skill level",
                'action': f"Look for more {ideal_difficulty} level content"
            })

        return recommendations

    def get_bias_aware_recommendations(
        self,
        user_id: int,
        count: int = 10,
        balance_bias: bool = True
    ) -> Dict:
        """
        Get recommendations that actively balance content bias.

        If balance_bias is True, will boost underexposed content types
        and topics in the recommendations.
        """
        # Get standard recommendations
        recommendations = self.get_recommendations_v2(
            user_id=user_id,
            count=count * 2,  # Get more to filter
            include_explanations=False
        )

        if not balance_bias:
            return recommendations

        # Get bias analysis
        bias = self.analyze_content_bias(user_id)

        if 'error' in bias:
            return recommendations

        underexposed_types = bias.get('bias_indicators', {}).get('underexposed_content_types', [])
        vark_alignment = bias.get('vark_content_alignment', 50)

        # Boost scores for courses that address bias
        boosted_recs = []
        for rec in recommendations.get('recommendations', []):
            course = rec.get('course', {})
            boost = 0

            # Boost for underexposed content
            course_tags = course.get('tags', [])
            if isinstance(course_tags, str):
                course_tags = course_tags.split(',')

            # If course addresses underexposed topics
            underexposed_topics = bias.get('bias_indicators', {}).get('underexposed_topics', [])
            for tag in course_tags:
                if tag.strip() in underexposed_topics:
                    boost += 10
                    rec['bias_correction'] = rec.get('bias_correction', []) + [f'Addresses underexposed topic: {tag}']

            # If user needs more interactive content and course has exercises
            if 'interactive' in underexposed_types:
                # Check if course description mentions exercises
                desc = course.get('description', '').lower()
                if any(word in desc for word in ['exercise', 'hands-on', 'practice', 'project']):
                    boost += 15
                    rec['bias_correction'] = rec.get('bias_correction', []) + ['Includes hands-on practice']

            # VARK alignment boost
            if vark_alignment < 40:
                from models import LearningStyle
                style = LearningStyle.query.filter_by(user_id=user_id).first()
                if style:
                    dominant = style.dominant_style
                    desc = course.get('description', '').lower()
                    title = course.get('title', '').lower()

                    vark_keywords = {
                        'VISUAL': ['video', 'diagram', 'visual', 'illustration'],
                        'AUDITORY': ['lecture', 'audio', 'discussion', 'explained'],
                        'KINESTHETIC': ['hands-on', 'project', 'coding', 'exercise', 'practice'],
                        'READING_WRITING': ['documentation', 'comprehensive', 'detailed', 'written']
                    }

                    if dominant in vark_keywords:
                        if any(kw in desc or kw in title for kw in vark_keywords[dominant]):
                            boost += 20
                            rec['bias_correction'] = rec.get('bias_correction', []) + [f'Matches your {dominant} learning style']

            rec['score'] = rec.get('score', 0) + boost
            rec['bias_boost'] = boost
            boosted_recs.append(rec)

        # Re-sort by boosted score
        boosted_recs.sort(key=lambda x: x['score'], reverse=True)

        return {
            'user_id': user_id,
            'recommendation_type': 'BIAS_AWARE',
            'bias_analysis': {
                'vark_alignment': bias.get('vark_content_alignment'),
                'underexposed_types': underexposed_types,
                'diversity_score': bias.get('topic_diversity_score')
            },
            'recommendations': boosted_recs[:count],
            'bias_corrections_applied': sum(1 for r in boosted_recs[:count] if r.get('bias_boost', 0) > 0)
        }