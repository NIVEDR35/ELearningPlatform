"""
Bias Monitoring and Fairness Module for Adaptive Learning Platform

This module monitors and mitigates bias in:
1. Course recommendations
2. Learning style inference
3. Content personalization
4. User profiling
"""

from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np
from models import db, User, Course, CourseRecommendation, UserInteraction, LearningStyle
from datetime import datetime, timedelta

class BiasMonitor:
    """Monitor and detect bias in ML recommendations"""
    
    def __init__(self):
        self.bias_threshold = 0.15  # 15% disparity threshold
        self.min_sample_size = 10
    
    def analyze_recommendation_bias(self) -> Dict:
        """Comprehensive bias analysis of recommendation system"""
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_fairness_score': 0.0,
            'bias_detected': False,
            'analyses': {}
        }
        
        # 1. Difficulty Distribution Bias
        results['analyses']['difficulty_bias'] = self._check_difficulty_bias()
        
        # 2. Learning Style Bias
        results['analyses']['learning_style_bias'] = self._check_learning_style_bias()
        
        # 3. Popularity Bias (filter bubble)
        results['analyses']['popularity_bias'] = self._check_popularity_bias()
        
        # 4. Temporal Bias (recency bias)
        results['analyses']['temporal_bias'] = self._check_temporal_bias()
        
        # 5. Content Diversity
        results['analyses']['diversity_score'] = self._check_diversity()
        
        # Calculate overall fairness score
        fairness_scores = []
        for analysis in results['analyses'].values():
            if 'fairness_score' in analysis:
                fairness_scores.append(analysis['fairness_score'])
        
        if fairness_scores:
            results['overall_fairness_score'] = np.mean(fairness_scores)
            results['bias_detected'] = results['overall_fairness_score'] < 0.85
        
        return results
    
    def _check_difficulty_bias(self) -> Dict:
        """Check if recommendations are biased towards certain difficulty levels"""
        
        # Get all recommendations
        recommendations = CourseRecommendation.query.all()
        
        if len(recommendations) < self.min_sample_size:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough recommendations to analyze'
            }
        
        # Count recommendations by difficulty
        difficulty_counts = defaultdict(int)
        total = 0
        
        for rec in recommendations:
            course = Course.query.get(rec.course_id)
            if course:
                difficulty_counts[course.difficulty] += 1
                total += 1
        
        # Calculate distribution
        distribution = {
            diff: count / total if total > 0 else 0
            for diff, count in difficulty_counts.items()
        }
        
        # Expected uniform distribution
        expected = 1.0 / len(difficulty_counts) if difficulty_counts else 0
        
        # Calculate disparity
        max_disparity = max(
            abs(dist - expected) for dist in distribution.values()
        ) if distribution else 0
        
        fairness_score = 1.0 - min(max_disparity / expected, 1.0) if expected > 0 else 1.0
        
        return {
            'distribution': dict(distribution),
            'expected_uniform': expected,
            'max_disparity': max_disparity,
            'fairness_score': fairness_score,
            'bias_detected': max_disparity > self.bias_threshold,
            'recommendation': self._get_difficulty_recommendation(max_disparity)
        }
    
    def _check_learning_style_bias(self) -> Dict:
        """Check if certain learning styles are over/under-represented"""
        
        # Get all learning styles
        styles = LearningStyle.query.all()
        
        if len(styles) < self.min_sample_size:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough learning style data'
            }
        
        # Count by dominant style
        style_counts = defaultdict(int)
        for style in styles:
            style_counts[style.dominant_style] += 1
        
        total = len(styles)
        distribution = {
            style: count / total
            for style, count in style_counts.items()
        }
        
        # Check if any style is severely underrepresented
        expected = 1.0 / 4  # 4 VARK styles
        max_disparity = max(
            abs(dist - expected) for dist in distribution.values()
        ) if distribution else 0
        
        fairness_score = 1.0 - min(max_disparity / expected, 1.0) if expected > 0 else 1.0
        
        return {
            'distribution': dict(distribution),
            'expected_uniform': expected,
            'max_disparity': max_disparity,
            'fairness_score': fairness_score,
            'bias_detected': max_disparity > self.bias_threshold,
            'recommendation': 'Ensure diverse content types for all learning styles'
        }
    
    def _check_popularity_bias(self) -> Dict:
        """Check for filter bubble / popularity bias"""
        
        # Get recommendations
        recommendations = CourseRecommendation.query.all()
        
        if len(recommendations) < self.min_sample_size:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough recommendations'
            }
        
        # Calculate course popularity
        course_popularity = {}
        all_courses = Course.query.all()
        
        for course in all_courses:
            enrollment_count = UserInteraction.query.filter_by(
                resource_type='COURSE',
                resource_id=course.id
            ).distinct(UserInteraction.user_id).count()
            course_popularity[course.id] = enrollment_count
        
        # Check if recommendations favor popular courses
        recommended_course_ids = [rec.course_id for rec in recommendations]
        avg_popularity_recommended = np.mean([
            course_popularity.get(cid, 0) for cid in recommended_course_ids
        ]) if recommended_course_ids else 0
        
        avg_popularity_all = np.mean(list(course_popularity.values())) if course_popularity else 0
        
        # Calculate bias ratio
        bias_ratio = (
            avg_popularity_recommended / avg_popularity_all
            if avg_popularity_all > 0 else 1.0
        )
        
        # Fairness score (1.0 = no bias, lower = more bias)
        fairness_score = 1.0 / bias_ratio if bias_ratio > 1.0 else bias_ratio
        
        return {
            'avg_popularity_recommended': avg_popularity_recommended,
            'avg_popularity_all': avg_popularity_all,
            'bias_ratio': bias_ratio,
            'fairness_score': fairness_score,
            'bias_detected': bias_ratio > 1.5 or bias_ratio < 0.67,
            'recommendation': self._get_popularity_recommendation(bias_ratio)
        }
    
    def _check_temporal_bias(self) -> Dict:
        """Check for recency bias in recommendations"""
        
        recommendations = CourseRecommendation.query.all()
        
        if len(recommendations) < self.min_sample_size:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough recommendations'
            }
        
        # Get course creation dates
        now = datetime.utcnow()
        course_ages = []
        
        for rec in recommendations:
            course = Course.query.get(rec.course_id)
            if course and course.created_at:
                age_days = (now - course.created_at).days
                course_ages.append(age_days)
        
        if not course_ages:
            return {'status': 'no_data'}
        
        avg_age = np.mean(course_ages)
        std_age = np.std(course_ages)
        
        # Check if heavily biased towards new courses
        recency_bias_detected = avg_age < 30 and std_age < 15
        
        fairness_score = min(avg_age / 90, 1.0)  # Normalize to 90 days
        
        return {
            'avg_course_age_days': avg_age,
            'std_course_age_days': std_age,
            'fairness_score': fairness_score,
            'bias_detected': recency_bias_detected,
            'recommendation': 'Balance new and established courses'
        }
    
    def _check_diversity(self) -> Dict:
        """Check diversity of recommended courses"""
        
        recommendations = CourseRecommendation.query.all()
        
        if len(recommendations) < self.min_sample_size:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough recommendations'
            }
        
        # Get unique courses, tags, difficulties
        unique_courses = len(set(rec.course_id for rec in recommendations))
        total_recommendations = len(recommendations)
        
        # Get tag diversity
        all_tags = set()
        for rec in recommendations:
            course = Course.query.get(rec.course_id)
            if course and course.tags:
                tags = [t.strip() for t in course.tags.split(',')]
                all_tags.update(tags)
        
        # Calculate diversity scores
        course_diversity = unique_courses / total_recommendations if total_recommendations > 0 else 0
        tag_diversity = len(all_tags)
        
        # Overall diversity score
        diversity_score = (course_diversity + min(tag_diversity / 20, 1.0)) / 2
        
        return {
            'unique_courses': unique_courses,
            'total_recommendations': total_recommendations,
            'course_diversity_ratio': course_diversity,
            'unique_tags': len(all_tags),
            'diversity_score': diversity_score,
            'fairness_score': diversity_score,
            'bias_detected': diversity_score < 0.5,
            'recommendation': 'Increase content diversity' if diversity_score < 0.5 else 'Good diversity'
        }
    
    def _get_difficulty_recommendation(self, disparity: float) -> str:
        """Get recommendation for difficulty bias"""
        if disparity < 0.1:
            return 'Excellent balance across difficulty levels'
        elif disparity < 0.2:
            return 'Good balance, minor adjustments recommended'
        else:
            return 'Significant bias detected - diversify difficulty recommendations'
    
    def _get_popularity_recommendation(self, ratio: float) -> str:
        """Get recommendation for popularity bias"""
        if 0.8 <= ratio <= 1.2:
            return 'Good balance between popular and niche courses'
        elif ratio > 1.5:
            return 'Too focused on popular courses - recommend more niche content'
        else:
            return 'Too focused on unpopular courses - balance with proven content'
    
    def generate_bias_report(self) -> str:
        """Generate human-readable bias report"""
        
        analysis = self.analyze_recommendation_bias()
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║           BIAS MONITORING REPORT - ADAPTIVE LEARNING PLATFORM        ║
╚══════════════════════════════════════════════════════════════════════╝

Generated: {analysis['timestamp']}

OVERALL FAIRNESS SCORE: {analysis['overall_fairness_score']:.2%}
STATUS: {'⚠️  BIAS DETECTED' if analysis['bias_detected'] else '✅ FAIR SYSTEM'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DIFFICULTY DISTRIBUTION BIAS
"""
        
        diff_bias = analysis['analyses'].get('difficulty_bias', {})
        if 'fairness_score' in diff_bias:
            report += f"""
   Fairness Score: {diff_bias['fairness_score']:.2%}
   Status: {'❌ BIASED' if diff_bias['bias_detected'] else '✅ FAIR'}
   
   Distribution:
"""
            for diff, pct in diff_bias.get('distribution', {}).items():
                report += f"   - {diff}: {pct:.1%}\n"
            report += f"\n   Recommendation: {diff_bias.get('recommendation', 'N/A')}\n"
        
        report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LEARNING STYLE BIAS
"""
        
        style_bias = analysis['analyses'].get('learning_style_bias', {})
        if 'fairness_score' in style_bias:
            report += f"""
   Fairness Score: {style_bias['fairness_score']:.2%}
   Status: {'❌ BIASED' if style_bias['bias_detected'] else '✅ FAIR'}
   
   Distribution:
"""
            for style, pct in style_bias.get('distribution', {}).items():
                report += f"   - {style}: {pct:.1%}\n"
        
        report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. POPULARITY BIAS (Filter Bubble)
"""
        
        pop_bias = analysis['analyses'].get('popularity_bias', {})
        if 'fairness_score' in pop_bias:
            report += f"""
   Fairness Score: {pop_bias['fairness_score']:.2%}
   Status: {'❌ BIASED' if pop_bias['bias_detected'] else '✅ FAIR'}
   Bias Ratio: {pop_bias.get('bias_ratio', 0):.2f}
   
   Recommendation: {pop_bias.get('recommendation', 'N/A')}
"""
        
        report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. CONTENT DIVERSITY
"""
        
        diversity = analysis['analyses'].get('diversity_score', {})
        if 'diversity_score' in diversity:
            report += f"""
   Diversity Score: {diversity['diversity_score']:.2%}
   Unique Courses: {diversity.get('unique_courses', 0)}
   Unique Tags: {diversity.get('unique_tags', 0)}
   
   Recommendation: {diversity.get('recommendation', 'N/A')}
"""
        
        report += """
╚══════════════════════════════════════════════════════════════════════╝
"""
        
        return report
    
    def get_mitigation_strategies(self, analysis: Dict) -> List[str]:
        """Get strategies to mitigate detected biases"""
        
        strategies = []
        
        for bias_type, data in analysis['analyses'].items():
            if data.get('bias_detected'):
                if bias_type == 'difficulty_bias':
                    strategies.append(
                        "Add diversity penalty in recommendation scoring to balance difficulty levels"
                    )
                elif bias_type == 'learning_style_bias':
                    strategies.append(
                        "Ensure content library has balanced representation for all VARK styles"
                    )
                elif bias_type == 'popularity_bias':
                    strategies.append(
                        "Implement exploration bonus for less popular but high-quality courses"
                    )
                elif bias_type == 'temporal_bias':
                    strategies.append(
                        "Add temporal diversity to prevent recency bias"
                    )
                elif bias_type == 'diversity_score':
                    strategies.append(
                        "Increase content variety and tag diversity in recommendations"
                    )
        
        if not strategies:
            strategies.append("System is fair - continue monitoring")
        
        return strategies
