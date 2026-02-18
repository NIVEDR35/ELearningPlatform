"""
Content Cache Service
Provides local caching for AI-generated content to reduce API calls and enable faster responses.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from models import db, GeneratedContent


class ContentCacheService:
    """Cache AI-generated content to reduce API calls and improve response times"""

    # Default cache validity in days
    DEFAULT_CACHE_VALIDITY_DAYS = 30

    # Maximum cache entries per content type
    MAX_CACHE_ENTRIES = 1000

    def __init__(self, cache_validity_days: int = None):
        self.cache_validity_days = cache_validity_days or self.DEFAULT_CACHE_VALIDITY_DAYS

    def generate_cache_key(self, content_type: str, **params) -> str:
        """
        Generate a unique cache key based on generation parameters.

        Args:
            content_type: Type of content (COURSE, QUIZ, ASSIGNMENT, etc.)
            **params: Generation parameters to hash

        Returns:
            SHA-256 hash string
        """
        # Sort params to ensure consistent hashing
        sorted_params = {k: v for k, v in sorted(params.items()) if v is not None}
        param_str = json.dumps(sorted_params, sort_keys=True, default=str)
        full_key = f"{content_type}:{param_str}"

        return hashlib.sha256(full_key.encode()).hexdigest()

    def get_cached_content(self, cache_key: str) -> Optional[Dict]:
        """
        Retrieve cached content if valid.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached content dict or None if not found/invalid
        """
        try:
            cached = GeneratedContent.query.filter_by(
                content_hash=cache_key,
                is_valid=True
            ).first()

            if not cached:
                return None

            # Check if cache has expired
            expiry_date = cached.created_at + timedelta(days=self.cache_validity_days)
            if datetime.utcnow() > expiry_date:
                cached.is_valid = False
                db.session.commit()
                return None

            # Check explicit expiration
            if cached.expires_at and datetime.utcnow() > cached.expires_at:
                cached.is_valid = False
                db.session.commit()
                return None

            # Update access stats
            cached.last_accessed = datetime.utcnow()
            cached.access_count += 1
            db.session.commit()

            return json.loads(cached.content_json)

        except Exception as e:
            print(f"Error retrieving cached content: {str(e)}")
            return None

    def cache_content(
        self,
        cache_key: str,
        content: Dict,
        content_type: str,
        topic: str = None,
        difficulty: str = None,
        learning_style: str = None,
        user_level: str = None,
        generation_params: Dict = None,
        expires_in_days: int = None
    ) -> bool:
        """
        Store generated content in cache.

        Args:
            cache_key: Unique cache key
            content: Content to cache
            content_type: Type of content
            topic: Topic of the content
            difficulty: Difficulty level
            learning_style: Learning style the content is adapted for
            user_level: User's skill level
            generation_params: Additional generation parameters
            expires_in_days: Custom expiration (overrides default)

        Returns:
            True if caching successful, False otherwise
        """
        try:
            # Check if entry exists
            existing = GeneratedContent.query.filter_by(content_hash=cache_key).first()

            if existing:
                # Update existing entry
                existing.content_json = json.dumps(content, default=str)
                existing.version += 1
                existing.is_valid = True
                existing.last_accessed = datetime.utcnow()
                existing.usage_count += 1

                if expires_in_days:
                    existing.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            else:
                # Create new entry
                cached = GeneratedContent(
                    content_type=content_type,
                    content_hash=cache_key,
                    topic=topic,
                    difficulty=difficulty,
                    learning_style=learning_style,
                    user_level=user_level,
                    generation_params=json.dumps(generation_params) if generation_params else None,
                    content_json=json.dumps(content, default=str),
                    expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
                )
                db.session.add(cached)

            db.session.commit()

            # Cleanup old entries if needed
            self._cleanup_old_entries(content_type)

            return True

        except Exception as e:
            print(f"Error caching content: {str(e)}")
            db.session.rollback()
            return False

    def get_or_generate(
        self,
        content_type: str,
        generator_func: callable,
        topic: str = None,
        difficulty: str = None,
        learning_style: str = None,
        user_level: str = None,
        force_regenerate: bool = False,
        **generation_params
    ) -> Dict:
        """
        Get cached content or generate new content if not cached.

        Args:
            content_type: Type of content
            generator_func: Function to call for generation if not cached
            topic: Topic for cache key
            difficulty: Difficulty for cache key
            learning_style: Learning style for cache key
            user_level: User level for cache key
            force_regenerate: Skip cache and regenerate
            **generation_params: Additional params for cache key and generator

        Returns:
            Content dict (from cache or freshly generated)
        """
        # Build cache key params
        key_params = {
            'topic': topic,
            'difficulty': difficulty,
            'learning_style': learning_style,
            'user_level': user_level,
            **generation_params
        }

        cache_key = self.generate_cache_key(content_type, **key_params)

        # Try cache first (unless force regenerate)
        if not force_regenerate:
            cached = self.get_cached_content(cache_key)
            if cached:
                print(f"Cache hit for {content_type}: {topic}")
                return cached

        print(f"Cache miss for {content_type}: {topic}, generating new content...")

        # Generate new content
        content = generator_func()

        # Cache the result
        if content:
            self.cache_content(
                cache_key=cache_key,
                content=content,
                content_type=content_type,
                topic=topic,
                difficulty=difficulty,
                learning_style=learning_style,
                user_level=user_level,
                generation_params=generation_params
            )

        return content

    def invalidate_cache(
        self,
        content_type: str = None,
        topic: str = None,
        cache_key: str = None
    ) -> int:
        """
        Invalidate cached content.

        Args:
            content_type: Invalidate all of this type
            topic: Invalidate all for this topic
            cache_key: Invalidate specific cache key

        Returns:
            Number of entries invalidated
        """
        try:
            query = GeneratedContent.query.filter_by(is_valid=True)

            if cache_key:
                query = query.filter_by(content_hash=cache_key)
            else:
                if content_type:
                    query = query.filter_by(content_type=content_type)
                if topic:
                    query = query.filter_by(topic=topic)

            count = query.update({'is_valid': False})
            db.session.commit()

            return count

        except Exception as e:
            print(f"Error invalidating cache: {str(e)}")
            db.session.rollback()
            return 0

    def record_feedback(self, cache_key: str, positive: bool) -> bool:
        """
        Record user feedback on cached content.

        Args:
            cache_key: The cache key
            positive: True for positive feedback, False for negative

        Returns:
            True if feedback recorded
        """
        try:
            cached = GeneratedContent.query.filter_by(content_hash=cache_key).first()

            if cached:
                if positive:
                    cached.positive_feedback = (cached.positive_feedback or 0) + 1
                else:
                    cached.negative_feedback = (cached.negative_feedback or 0) + 1

                # Update quality score
                total_feedback = (cached.positive_feedback or 0) + (cached.negative_feedback or 0)
                if total_feedback > 0:
                    cached.quality_score = ((cached.positive_feedback or 0) / total_feedback) * 100

                db.session.commit()
                return True

            return False

        except Exception as e:
            print(f"Error recording feedback: {str(e)}")
            return False

    def get_cache_stats(self, content_type: str = None) -> Dict:
        """
        Get cache statistics.

        Args:
            content_type: Filter by content type

        Returns:
            Statistics dict
        """
        try:
            query = GeneratedContent.query

            if content_type:
                query = query.filter_by(content_type=content_type)

            total = query.count()
            valid = query.filter_by(is_valid=True).count()

            # Get average access count
            from sqlalchemy import func
            avg_access = db.session.query(
                func.avg(GeneratedContent.access_count)
            ).filter_by(is_valid=True).scalar() or 0

            # Get average quality score
            avg_quality = db.session.query(
                func.avg(GeneratedContent.quality_score)
            ).filter(
                GeneratedContent.quality_score.isnot(None)
            ).scalar() or 0

            # Get content type breakdown
            type_counts = db.session.query(
                GeneratedContent.content_type,
                func.count(GeneratedContent.id)
            ).filter_by(is_valid=True).group_by(
                GeneratedContent.content_type
            ).all()

            return {
                'total_entries': total,
                'valid_entries': valid,
                'invalid_entries': total - valid,
                'average_access_count': round(avg_access, 2),
                'average_quality_score': round(avg_quality, 2),
                'entries_by_type': {t: c for t, c in type_counts},
                'cache_validity_days': self.cache_validity_days
            }

        except Exception as e:
            print(f"Error getting cache stats: {str(e)}")
            return {}

    def _cleanup_old_entries(self, content_type: str) -> int:
        """
        Clean up old entries to prevent cache from growing too large.

        Args:
            content_type: Content type to clean up

        Returns:
            Number of entries removed
        """
        try:
            # Count current entries
            count = GeneratedContent.query.filter_by(
                content_type=content_type,
                is_valid=True
            ).count()

            if count <= self.MAX_CACHE_ENTRIES:
                return 0

            # Find entries to invalidate (oldest, least accessed)
            entries_to_remove = count - self.MAX_CACHE_ENTRIES + 100  # Remove 100 extra for buffer

            old_entries = GeneratedContent.query.filter_by(
                content_type=content_type,
                is_valid=True
            ).order_by(
                GeneratedContent.last_accessed.asc(),
                GeneratedContent.access_count.asc()
            ).limit(entries_to_remove).all()

            for entry in old_entries:
                entry.is_valid = False

            db.session.commit()
            return len(old_entries)

        except Exception as e:
            print(f"Error cleaning up cache: {str(e)}")
            return 0

    def get_similar_content(
        self,
        content_type: str,
        topic: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find similar cached content that might be relevant.

        Args:
            content_type: Type of content
            topic: Topic to match
            limit: Maximum results

        Returns:
            List of similar content entries
        """
        try:
            # Simple keyword matching for now
            # Could be enhanced with semantic similarity
            entries = GeneratedContent.query.filter(
                GeneratedContent.content_type == content_type,
                GeneratedContent.is_valid == True,
                GeneratedContent.topic.ilike(f"%{topic}%")
            ).order_by(
                GeneratedContent.quality_score.desc().nullslast(),
                GeneratedContent.access_count.desc()
            ).limit(limit).all()

            return [e.to_dict() for e in entries]

        except Exception as e:
            print(f"Error finding similar content: {str(e)}")
            return []


# Singleton instance
_cache_service = None

def get_cache_service() -> ContentCacheService:
    """Get the singleton cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = ContentCacheService()
    return _cache_service
