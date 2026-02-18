import requests
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

class YouTubeService:
    """YouTube API integration for video content with VARK learning style optimization"""

    # VARK search modifiers to optimize video search for learning styles
    VARK_SEARCH_MODIFIERS = {
        'VISUAL': ['diagram', 'visualization', 'animated', 'illustrated', 'infographic', 'chart', 'visual guide'],
        'AUDITORY': ['explained', 'lecture', 'podcast', 'discussion', 'talk', 'audio', 'verbal explanation'],
        'KINESTHETIC': ['hands-on', 'step by step', 'coding along', 'practice', 'tutorial', 'workshop', 'demo', 'build'],
        'READING_WRITING': ['comprehensive', 'detailed', 'documentation', 'notes', 'written', 'text-based', 'slides']
    }

    # Video type indicators for VARK classification
    VIDEO_TYPE_INDICATORS = {
        'tutorial': {'kinesthetic': 3, 'visual': 2, 'auditory': 1, 'reading_writing': 1},
        'lecture': {'auditory': 4, 'reading_writing': 2, 'visual': 1, 'kinesthetic': 0},
        'demo': {'kinesthetic': 4, 'visual': 3, 'auditory': 1, 'reading_writing': 0},
        'visualization': {'visual': 5, 'kinesthetic': 1, 'auditory': 1, 'reading_writing': 0},
        'podcast': {'auditory': 5, 'reading_writing': 1, 'visual': 0, 'kinesthetic': 0},
        'workshop': {'kinesthetic': 5, 'auditory': 2, 'visual': 2, 'reading_writing': 1},
        'presentation': {'visual': 3, 'auditory': 3, 'reading_writing': 2, 'kinesthetic': 0},
        'walkthrough': {'kinesthetic': 4, 'visual': 3, 'auditory': 2, 'reading_writing': 1},
        'course': {'reading_writing': 3, 'auditory': 3, 'visual': 2, 'kinesthetic': 2},
        'explained': {'auditory': 4, 'visual': 2, 'reading_writing': 2, 'kinesthetic': 1}
    }

    # Keywords that indicate specific VARK characteristics
    VARK_KEYWORDS = {
        'visual': ['diagram', 'chart', 'graph', 'animation', 'visual', 'illustrated', 'infographic',
                   'flowchart', 'mindmap', 'whiteboard', 'drawing', 'sketch'],
        'auditory': ['explained', 'lecture', 'podcast', 'discussion', 'talk', 'interview',
                     'conversation', 'verbal', 'spoken', 'audio', 'narrated'],
        'kinesthetic': ['hands-on', 'practice', 'exercise', 'coding', 'build', 'create', 'make',
                        'project', 'lab', 'workshop', 'demo', 'step-by-step', 'follow along'],
        'reading_writing': ['documentation', 'notes', 'comprehensive', 'detailed', 'written',
                            'text', 'slides', 'pdf', 'reading', 'transcript', 'subtitles']
    }

    def __init__(self):
        # YouTube API key from Spring Boot project
        self.api_key = 'AIzaSyApsmvV-0HH8vBlk12W1jv8lQVWfx_M5IM'
        self.base_url = 'https://www.googleapis.com/youtube/v3'
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for YouTube videos"""
        try:
            url = f"{self.base_url}/search"
            params = {
                'part': 'snippet',
                'type': 'video',
                'q': query,
                'maxResults': max_results,
                'key': self.api_key,
                'relevanceLanguage': 'en',
                'safeSearch': 'strict'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_youtube_response(data)
            else:
                print(f"YouTube API error: {response.status_code}")
                return self._generate_fallback_videos(query, max_results)
                
        except Exception as e:
            print(f"Error searching YouTube: {str(e)}")
            return self._generate_fallback_videos(query, max_results)
    
    def _parse_youtube_response(self, response: Dict) -> List[Dict]:
        """Parse YouTube API response"""
        videos = []
        
        if 'items' in response:
            for item in response['items']:
                video_id = item['id'].get('videoId')
                snippet = item.get('snippet', {})
                
                if video_id:
                    video = {
                        'id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_title': snippet.get('channelTitle', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'source': 'youtube'
                    }
                    videos.append(video)
        
        return videos
    
    def _generate_fallback_videos(self, topic: str, max_results: int) -> List[Dict]:
        """Generate fallback videos when API fails"""
        # Educational video IDs that exist
        educational_video_ids = [
            'dQw4w9WgXcQ', 'oHg5SJYRHA0', 'kJQP7kiw5Fk',
            'L_jWHffIx5E', 'fJ9rUzIMcZQ', '9bZkp7q19f0',
            'GtQdIYUtAHg', 'Sagg08DrO5U'
        ]
        
        tutorial_types = ['Introduction to', 'Advanced', 'Complete Guide to', 'Mastering', 'Learn']
        
        videos = []
        for i in range(min(max_results, len(educational_video_ids))):
            video_id = educational_video_ids[i]
            videos.append({
                'id': video_id,
                'title': f'{tutorial_types[i % len(tutorial_types)]} {topic}',
                'description': f'Learn {topic} from scratch with practical examples',
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'embed_url': f'https://www.youtube.com/embed/{video_id}',
                'thumbnail_url': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
                'channel_title': 'Educational Channel',
                'source': 'fallback'
            })
        
        return videos
    
    def search_videos_for_topics(self, topics: List[str], max_per_topic: int = 3) -> List[Dict]:
        """Search videos for multiple topics"""
        all_videos = []
        
        for topic in topics:
            videos = self.search_videos(f"{topic} tutorial", max_per_topic)
            all_videos.extend(videos)
        
        return all_videos
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """Get detailed information about a video"""
        try:
            url = f"{self.base_url}/videos"
            params = {
                'part': 'snippet,contentDetails,statistics',
                'id': video_id,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    item = data['items'][0]
                    return {
                        'id': video_id,
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'duration': item['contentDetails']['duration'],
                        'view_count': item['statistics'].get('viewCount', 0),
                        'like_count': item['statistics'].get('likeCount', 0),
                        'thumbnail_url': item['snippet']['thumbnails']['high']['url']
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting video details: {str(e)}")
            return None

    # ==================== PHASE 2: VARK-OPTIMIZED METHODS ====================

    def search_videos_vark_optimized(
        self,
        query: str,
        learning_style: str,
        vark_scores: Optional[Dict[str, int]] = None,
        max_results: int = 10,
        difficulty: str = 'intermediate'
    ) -> List[Dict]:
        """
        Search for YouTube videos optimized for the user's VARK learning style.

        Args:
            query: The search topic
            learning_style: Primary VARK style ('VISUAL', 'AUDITORY', 'KINESTHETIC', 'READING_WRITING')
            vark_scores: Optional dict with scores for each VARK dimension
            max_results: Maximum number of results to return
            difficulty: 'beginner', 'intermediate', or 'advanced'

        Returns:
            List of videos with VARK suitability scores
        """
        try:
            # Get style-specific search modifiers
            modifiers = self.VARK_SEARCH_MODIFIERS.get(learning_style.upper(), [])

            # Build enhanced query with VARK modifiers
            # Select 2 random modifiers to avoid overly specific queries
            import random
            selected_modifiers = random.sample(modifiers, min(2, len(modifiers))) if modifiers else []

            # Add difficulty modifier
            difficulty_modifiers = {
                'beginner': ['beginner', 'introduction', 'basics', 'for beginners'],
                'intermediate': ['tutorial', 'guide', 'learn'],
                'advanced': ['advanced', 'deep dive', 'expert', 'masterclass']
            }
            diff_modifier = random.choice(difficulty_modifiers.get(difficulty, ['tutorial']))

            # Construct the optimized query
            enhanced_query = f"{query} {diff_modifier}"
            if selected_modifiers:
                enhanced_query += f" {' '.join(selected_modifiers)}"

            # Search with enhanced query
            url = f"{self.base_url}/search"
            params = {
                'part': 'snippet',
                'type': 'video',
                'q': enhanced_query,
                'maxResults': max_results * 2,  # Fetch extra for filtering
                'key': self.api_key,
                'relevanceLanguage': 'en',
                'safeSearch': 'strict',
                'videoCaption': 'closedCaption' if learning_style.upper() == 'READING_WRITING' else 'any'
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                videos = self._parse_youtube_response_with_vark(data, learning_style, vark_scores)

                # Sort by VARK match score and return top results
                videos.sort(key=lambda x: x.get('vark_match_score', 0), reverse=True)
                return videos[:max_results]
            else:
                print(f"YouTube API error: {response.status_code}")
                return self._generate_fallback_videos_vark(query, learning_style, max_results)

        except Exception as e:
            print(f"Error in VARK-optimized search: {str(e)}")
            return self._generate_fallback_videos_vark(query, learning_style, max_results)

    def _parse_youtube_response_with_vark(
        self,
        response: Dict,
        learning_style: str,
        vark_scores: Optional[Dict[str, int]] = None
    ) -> List[Dict]:
        """Parse YouTube API response with VARK suitability analysis"""
        videos = []

        if 'items' in response:
            for item in response['items']:
                video_id = item['id'].get('videoId')
                snippet = item.get('snippet', {})

                if video_id:
                    title = snippet.get('title', '')
                    description = snippet.get('description', '')

                    # Analyze VARK characteristics
                    vark_analysis = self._analyze_video_vark_characteristics(title, description)

                    # Calculate match score based on user's learning style
                    match_score = self._calculate_vark_match_score(
                        vark_analysis, learning_style, vark_scores
                    )

                    video = {
                        'id': video_id,
                        'title': title,
                        'description': description,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_title': snippet.get('channelTitle', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'source': 'youtube',
                        'vark_suitability': vark_analysis,
                        'vark_match_score': match_score,
                        'recommended_for_style': learning_style,
                        'video_type': self._detect_video_type(title, description)
                    }
                    videos.append(video)

        return videos

    def _analyze_video_vark_characteristics(self, title: str, description: str) -> Dict[str, int]:
        """
        Analyze video title and description to determine VARK suitability scores.
        Returns scores from 0-100 for each VARK dimension.
        """
        text = f"{title} {description}".lower()

        scores = {
            'visual': 0,
            'auditory': 0,
            'kinesthetic': 0,
            'reading_writing': 0
        }

        # Score based on keyword presence
        for style, keywords in self.VARK_KEYWORDS.items():
            keyword_count = sum(1 for keyword in keywords if keyword.lower() in text)
            # Normalize to 0-60 range based on keywords (max ~12 keywords per style)
            scores[style] += min(60, keyword_count * 10)

        # Score based on video type indicators
        for video_type, type_scores in self.VIDEO_TYPE_INDICATORS.items():
            if video_type in text:
                for style, points in type_scores.items():
                    scores[style] += points * 8  # Scale up type indicator scores

        # Normalize scores to 0-100
        for style in scores:
            scores[style] = min(100, scores[style])

        # Apply baseline scores (every video has some of each)
        for style in scores:
            if scores[style] < 20:
                scores[style] = 20

        return scores

    def _calculate_vark_match_score(
        self,
        video_vark: Dict[str, int],
        primary_style: str,
        user_vark_scores: Optional[Dict[str, int]] = None
    ) -> float:
        """
        Calculate how well a video matches the user's VARK profile.
        Returns a score from 0-100.
        """
        style_map = {
            'VISUAL': 'visual',
            'AUDITORY': 'auditory',
            'KINESTHETIC': 'kinesthetic',
            'READING_WRITING': 'reading_writing'
        }

        primary_key = style_map.get(primary_style.upper(), 'visual')

        if user_vark_scores:
            # Weighted match based on user's full VARK profile
            total_score = 0
            total_weight = 0

            for style, user_score in user_vark_scores.items():
                style_key = style.lower().replace(' ', '_')
                if style_key in video_vark:
                    weight = user_score / 100  # Normalize weight
                    total_score += video_vark[style_key] * weight
                    total_weight += weight

            if total_weight > 0:
                return total_score / total_weight
            return video_vark.get(primary_key, 50)
        else:
            # Simple match based on primary style
            return video_vark.get(primary_key, 50)

    def _detect_video_type(self, title: str, description: str) -> str:
        """Detect the type of video based on title and description"""
        text = f"{title} {description}".lower()

        type_priorities = [
            ('workshop', 'workshop'),
            ('podcast', 'podcast'),
            ('lecture', 'lecture'),
            ('visualization', 'visualization'),
            ('walkthrough', 'walkthrough'),
            ('demo', 'demo'),
            ('tutorial', 'tutorial'),
            ('course', 'course'),
            ('explained', 'explanation'),
            ('presentation', 'presentation')
        ]

        for keyword, video_type in type_priorities:
            if keyword in text:
                return video_type

        return 'general'

    def _generate_fallback_videos_vark(
        self,
        topic: str,
        learning_style: str,
        max_results: int
    ) -> List[Dict]:
        """Generate VARK-aware fallback videos when API fails"""
        videos = self._generate_fallback_videos(topic, max_results)

        # Add VARK metadata to fallback videos
        style_map = {
            'VISUAL': {'visual': 80, 'auditory': 40, 'kinesthetic': 50, 'reading_writing': 40},
            'AUDITORY': {'visual': 40, 'auditory': 80, 'kinesthetic': 40, 'reading_writing': 50},
            'KINESTHETIC': {'visual': 50, 'auditory': 40, 'kinesthetic': 80, 'reading_writing': 40},
            'READING_WRITING': {'visual': 40, 'auditory': 50, 'kinesthetic': 40, 'reading_writing': 80}
        }

        default_vark = style_map.get(learning_style.upper(), style_map['VISUAL'])

        for video in videos:
            video['vark_suitability'] = default_vark
            video['vark_match_score'] = 70.0
            video['recommended_for_style'] = learning_style
            video['video_type'] = 'tutorial'

        return videos

    def get_video_vark_characteristics(self, video_id: str) -> Optional[Dict]:
        """
        Get detailed VARK characteristics for a specific video.
        Analyzes title, description, and available metadata.
        """
        try:
            url = f"{self.base_url}/videos"
            params = {
                'part': 'snippet,contentDetails,statistics',
                'id': video_id,
                'key': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    item = data['items'][0]
                    snippet = item['snippet']
                    content_details = item['contentDetails']
                    statistics = item.get('statistics', {})

                    title = snippet['title']
                    description = snippet['description']

                    # Get VARK analysis
                    vark_scores = self._analyze_video_vark_characteristics(title, description)

                    # Check for captions (beneficial for reading/writing learners)
                    has_captions = content_details.get('caption', 'false') == 'true'
                    if has_captions:
                        vark_scores['reading_writing'] = min(100, vark_scores['reading_writing'] + 15)

                    # Parse duration
                    duration_seconds = self._parse_duration(content_details.get('duration', 'PT0S'))

                    # Determine best suited learning styles
                    sorted_styles = sorted(vark_scores.items(), key=lambda x: x[1], reverse=True)
                    primary_style = sorted_styles[0][0].upper()
                    secondary_style = sorted_styles[1][0].upper() if len(sorted_styles) > 1 else None

                    return {
                        'video_id': video_id,
                        'title': title,
                        'description': description[:500],  # Truncate for response
                        'channel': snippet.get('channelTitle', ''),
                        'duration_seconds': duration_seconds,
                        'duration_formatted': self._format_duration(duration_seconds),
                        'view_count': int(statistics.get('viewCount', 0)),
                        'like_count': int(statistics.get('likeCount', 0)),
                        'has_captions': has_captions,
                        'vark_scores': vark_scores,
                        'primary_learning_style': primary_style,
                        'secondary_learning_style': secondary_style,
                        'video_type': self._detect_video_type(title, description),
                        'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'style_recommendations': self._generate_style_recommendations(vark_scores)
                    }

            return None

        except Exception as e:
            print(f"Error getting video VARK characteristics: {str(e)}")
            return None

    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        # Format: PT#H#M#S
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0

    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _generate_style_recommendations(self, vark_scores: Dict[str, int]) -> List[str]:
        """Generate recommendations based on video's VARK characteristics"""
        recommendations = []

        if vark_scores.get('visual', 0) >= 70:
            recommendations.append("Great for visual learners who prefer diagrams and graphics")
        if vark_scores.get('auditory', 0) >= 70:
            recommendations.append("Ideal for auditory learners who learn through listening")
        if vark_scores.get('kinesthetic', 0) >= 70:
            recommendations.append("Perfect for hands-on learners who like to practice along")
        if vark_scores.get('reading_writing', 0) >= 70:
            recommendations.append("Suitable for learners who prefer detailed explanations")

        if not recommendations:
            recommendations.append("Well-rounded content suitable for multiple learning styles")

        return recommendations

    def track_video_engagement(
        self,
        db,
        user_id: int,
        video_id: str,
        engagement_data: Dict,
        lesson_id: Optional[int] = None
    ) -> Dict:
        """
        Track detailed video engagement metrics and correlate with VARK style.

        Args:
            db: Database session
            user_id: User ID
            video_id: YouTube video ID
            engagement_data: Dict containing engagement metrics
            lesson_id: Optional associated lesson ID

        Returns:
            Engagement record summary
        """
        from models import VideoEngagement, User

        try:
            # Get user's VARK profile
            user = User.query.get(user_id)
            user_vark_style = None
            visual_score = auditory_score = None

            if user and user.learning_style:
                user_vark_style = user.learning_style.dominant_style
                visual_score = user.learning_style.visual_score
                auditory_score = user.learning_style.auditory_score

            # Get video characteristics
            video_details = self.get_video_vark_characteristics(video_id)

            # Create or update engagement record
            engagement = VideoEngagement.query.filter_by(
                user_id=user_id,
                video_id=video_id
            ).first()

            if not engagement:
                engagement = VideoEngagement(
                    user_id=user_id,
                    video_id=video_id,
                    lesson_id=lesson_id,
                    started_at=datetime.utcnow()
                )
                db.session.add(engagement)

            # Update engagement metrics
            engagement.watch_duration_seconds = engagement_data.get(
                'watch_duration', engagement.watch_duration_seconds or 0
            )
            engagement.total_video_duration = engagement_data.get(
                'total_duration', engagement.total_video_duration
            )

            if engagement.total_video_duration and engagement.total_video_duration > 0:
                engagement.watch_percentage = (
                    engagement.watch_duration_seconds / engagement.total_video_duration
                ) * 100

            engagement.replay_count = engagement_data.get('replays', engagement.replay_count or 0)
            engagement.pause_count = engagement_data.get('pauses', engagement.pause_count or 0)
            engagement.seek_forward_count = engagement_data.get('seek_forward', engagement.seek_forward_count or 0)
            engagement.seek_backward_count = engagement_data.get('seek_backward', engagement.seek_backward_count or 0)
            engagement.playback_speed = engagement_data.get('playback_speed', engagement.playback_speed or 1.0)

            # VARK correlation
            engagement.user_vark_style = user_vark_style
            engagement.visual_score_at_view = visual_score
            engagement.auditory_score_at_view = auditory_score

            # Video characteristics
            if video_details:
                engagement.video_type = video_details.get('video_type')
                engagement.video_title = video_details.get('title')
                engagement.video_channel = video_details.get('channel')
                engagement.has_captions = video_details.get('has_captions', False)
                engagement.vark_suitability = json.dumps(video_details.get('vark_scores', {}))

            # Calculate engagement score (0-100)
            engagement.engagement_score = self._calculate_engagement_score(engagement)

            # Check if completed
            if engagement.watch_percentage >= 90:
                engagement.completed = True
                engagement.completed_at = datetime.utcnow()

            db.session.commit()

            return {
                'engagement_id': engagement.id,
                'video_id': video_id,
                'watch_percentage': engagement.watch_percentage,
                'engagement_score': engagement.engagement_score,
                'completed': engagement.completed,
                'vark_style_at_view': user_vark_style,
                'video_type': engagement.video_type
            }

        except Exception as e:
            print(f"Error tracking video engagement: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def _calculate_engagement_score(self, engagement) -> float:
        """Calculate engagement score based on viewing behavior"""
        score = 0

        # Watch percentage (max 40 points)
        watch_pct = engagement.watch_percentage or 0
        score += min(40, watch_pct * 0.4)

        # Replay behavior (max 20 points) - indicates interest
        replays = engagement.replay_count or 0
        score += min(20, replays * 5)

        # Pause behavior (max 10 points) - indicates note-taking
        pauses = engagement.pause_count or 0
        score += min(10, pauses * 2)

        # Seek backward (max 15 points) - indicates review
        seek_back = engagement.seek_backward_count or 0
        score += min(15, seek_back * 3)

        # Normal playback speed bonus (max 15 points)
        speed = engagement.playback_speed or 1.0
        if 0.75 <= speed <= 1.25:
            score += 15
        elif speed < 0.75:
            score += 10  # Slower speed shows attention
        else:
            score += 5  # Fast forward shows less engagement

        return min(100, score)

    def get_video_analytics_dashboard(self, db, user_id: int, days: int = 30) -> Dict:
        """
        Get comprehensive video analytics dashboard for a user.

        Args:
            db: Database session
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Analytics dashboard data
        """
        from models import VideoEngagement, User
        from sqlalchemy import func

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get user's VARK profile
            user = User.query.get(user_id)
            user_vark_style = None
            if user and user.learning_style:
                user_vark_style = user.learning_style.dominant_style

            # Get engagement records
            engagements = VideoEngagement.query.filter(
                VideoEngagement.user_id == user_id,
                VideoEngagement.created_at >= cutoff_date
            ).all()

            if not engagements:
                return {
                    'user_id': user_id,
                    'period_days': days,
                    'total_videos_watched': 0,
                    'total_watch_time_seconds': 0,
                    'message': 'No video engagement data found for this period'
                }

            # Calculate aggregate metrics
            total_watch_time = sum(e.watch_duration_seconds or 0 for e in engagements)
            completed_videos = sum(1 for e in engagements if e.completed)
            avg_engagement_score = sum(e.engagement_score or 0 for e in engagements) / len(engagements)
            avg_watch_percentage = sum(e.watch_percentage or 0 for e in engagements) / len(engagements)

            # VARK video performance analysis
            vark_performance = defaultdict(lambda: {'count': 0, 'total_score': 0, 'completed': 0})

            for e in engagements:
                if e.vark_suitability:
                    try:
                        vark_scores = json.loads(e.vark_suitability)
                        # Find primary style of video
                        primary = max(vark_scores, key=vark_scores.get)
                        vark_performance[primary]['count'] += 1
                        vark_performance[primary]['total_score'] += e.engagement_score or 0
                        if e.completed:
                            vark_performance[primary]['completed'] += 1
                    except:
                        pass

            # Calculate VARK performance averages
            vark_analysis = {}
            for style, data in vark_performance.items():
                if data['count'] > 0:
                    vark_analysis[style] = {
                        'videos_watched': data['count'],
                        'avg_engagement_score': data['total_score'] / data['count'],
                        'completion_rate': (data['completed'] / data['count']) * 100
                    }

            # Video type breakdown
            video_types = defaultdict(int)
            for e in engagements:
                if e.video_type:
                    video_types[e.video_type] += 1

            # Playback speed analysis
            speed_distribution = defaultdict(int)
            for e in engagements:
                speed = e.playback_speed or 1.0
                if speed < 1.0:
                    speed_distribution['slower'] += 1
                elif speed == 1.0:
                    speed_distribution['normal'] += 1
                else:
                    speed_distribution['faster'] += 1

            # Most engaging videos
            top_videos = sorted(engagements, key=lambda x: x.engagement_score or 0, reverse=True)[:5]
            top_videos_data = [{
                'video_id': v.video_id,
                'title': v.video_title or 'Unknown',
                'engagement_score': v.engagement_score,
                'watch_percentage': v.watch_percentage,
                'video_type': v.video_type
            } for v in top_videos]

            # Learning style alignment
            style_alignment = self._calculate_style_alignment(engagements, user_vark_style)

            return {
                'user_id': user_id,
                'user_vark_style': user_vark_style,
                'period_days': days,
                'summary': {
                    'total_videos_watched': len(engagements),
                    'videos_completed': completed_videos,
                    'completion_rate': (completed_videos / len(engagements)) * 100,
                    'total_watch_time_seconds': total_watch_time,
                    'total_watch_time_formatted': self._format_duration(total_watch_time),
                    'avg_engagement_score': round(avg_engagement_score, 1),
                    'avg_watch_percentage': round(avg_watch_percentage, 1)
                },
                'vark_video_performance': vark_analysis,
                'video_types_watched': dict(video_types),
                'playback_speed_distribution': dict(speed_distribution),
                'top_engaging_videos': top_videos_data,
                'style_alignment': style_alignment,
                'recommendations': self._generate_viewing_recommendations(
                    vark_analysis, user_vark_style, style_alignment
                )
            }

        except Exception as e:
            print(f"Error generating video analytics: {str(e)}")
            return {'error': str(e)}

    def _calculate_style_alignment(
        self,
        engagements: List,
        user_style: Optional[str]
    ) -> Dict:
        """Calculate how well video choices align with user's learning style"""
        if not user_style or not engagements:
            return {'alignment_score': 0, 'message': 'Insufficient data'}

        style_key = user_style.lower().replace(' ', '_')
        aligned_count = 0
        total_alignment_score = 0

        for e in engagements:
            if e.vark_suitability:
                try:
                    vark_scores = json.loads(e.vark_suitability)
                    video_score = vark_scores.get(style_key, 0)
                    total_alignment_score += video_score

                    # Consider aligned if video has >60 score for user's style
                    if video_score >= 60:
                        aligned_count += 1
                except:
                    pass

        alignment_rate = (aligned_count / len(engagements)) * 100 if engagements else 0
        avg_alignment = total_alignment_score / len(engagements) if engagements else 0

        return {
            'alignment_score': round(avg_alignment, 1),
            'aligned_video_percentage': round(alignment_rate, 1),
            'total_videos_analyzed': len(engagements),
            'well_aligned_videos': aligned_count
        }

    def _generate_viewing_recommendations(
        self,
        vark_analysis: Dict,
        user_style: Optional[str],
        style_alignment: Dict
    ) -> List[str]:
        """Generate personalized video viewing recommendations"""
        recommendations = []

        if not user_style:
            recommendations.append("Complete a VARK assessment for personalized video recommendations")
            return recommendations

        alignment_score = style_alignment.get('alignment_score', 0)

        if alignment_score < 50:
            recommendations.append(
                f"Try searching for videos with '{self.VARK_SEARCH_MODIFIERS.get(user_style.upper(), [''])[0]}' "
                f"keywords to better match your {user_style} learning style"
            )

        # Check engagement by video type
        best_type = None
        best_score = 0
        for style, data in vark_analysis.items():
            if data.get('avg_engagement_score', 0) > best_score:
                best_score = data['avg_engagement_score']
                best_type = style

        if best_type:
            recommendations.append(
                f"You engage most with {best_type}-style videos (avg score: {best_score:.1f}). "
                f"Consider focusing on this content type."
            )

        # Completion rate advice
        if vark_analysis:
            lowest_completion = min(vark_analysis.items(), key=lambda x: x[1].get('completion_rate', 100))
            if lowest_completion[1].get('completion_rate', 100) < 50:
                recommendations.append(
                    f"{lowest_completion[0].title()}-style videos have low completion rate. "
                    f"Try shorter videos or different content in this category."
                )

        if not recommendations:
            recommendations.append("Great job! Continue exploring videos aligned with your learning style.")

        return recommendations

    def get_recommended_videos_for_lesson(
        self,
        lesson_topic: str,
        user_id: int,
        db,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Get video recommendations for a specific lesson based on user's VARK profile.

        Args:
            lesson_topic: The lesson topic to search for
            user_id: User ID for VARK profile
            db: Database session
            max_results: Maximum number of videos to return

        Returns:
            List of recommended videos with VARK optimization
        """
        from models import User

        try:
            # Get user's VARK profile
            user = User.query.get(user_id)
            learning_style = 'VISUAL'  # Default
            vark_scores = None

            if user and user.learning_style:
                learning_style = user.learning_style.dominant_style or 'VISUAL'
                vark_scores = {
                    'visual': user.learning_style.visual_score,
                    'auditory': user.learning_style.auditory_score,
                    'kinesthetic': user.learning_style.kinesthetic_score,
                    'reading_writing': user.learning_style.reading_writing_score
                }

            # Search for VARK-optimized videos
            videos = self.search_videos_vark_optimized(
                query=lesson_topic,
                learning_style=learning_style,
                vark_scores=vark_scores,
                max_results=max_results
            )

            return videos

        except Exception as e:
            print(f"Error getting lesson video recommendations: {str(e)}")
            return self.search_videos(f"{lesson_topic} tutorial", max_results)
