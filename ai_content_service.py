"""
AI Content Generation Service
Advanced AI-driven content generation using Gemini AI with:
- Personalized course generation based on VARK learning styles
- Adaptive quiz generation based on performance history
- Skill-appropriate assignment generation
- Knowledge gap targeting
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from gemini_service import GeminiService
from content_cache_service import get_cache_service
from youtube_service import YouTubeService


class AIContentGenerationService:
    """Advanced AI content generation with personalization"""

    def __init__(self):
        self.gemini_service = GeminiService()
        self.cache_service = get_cache_service()
        self.youtube_service = YouTubeService()

    # ==================== LEARNING STYLE INSTRUCTIONS ====================

    def _get_learning_style_instructions(self, learning_style: str) -> str:
        """Get specific instructions for adapting content to learning style"""
        instructions = {
            'VISUAL': """
VISUAL LEARNER ADAPTATIONS:
- Include detailed diagram descriptions and visual metaphors
- Use spatial organization in explanations (top-down, left-right)
- Suggest flowcharts, mind maps, and infographics
- Use color-coded concepts and visual hierarchies
- Include "Picture this..." and "Imagine..." language
- Recommend video content with visual demonstrations
- Use tables and charts to organize information
""",
            'AUDITORY': """
AUDITORY LEARNER ADAPTATIONS:
- Use conversational, dialogue-style explanations
- Include discussion prompts and debate topics
- Suggest podcast-style summaries and verbal explanations
- Use mnemonic devices and rhymes
- Include "Listen to this..." and "Here's how it sounds..." language
- Recommend audio resources and verbal walkthroughs
- Structure content as if explaining to a friend
""",
            'KINESTHETIC': """
KINESTHETIC LEARNER ADAPTATIONS:
- Include hands-on exercises and practical projects
- Use real-world scenarios and simulations
- Provide step-by-step implementation guides
- Include "Try this..." and "Build this..." activities
- Focus on learning by doing with immediate feedback
- Recommend coding exercises and interactive labs
- Break concepts into actionable tasks
""",
            'READING_WRITING': """
READING/WRITING LEARNER ADAPTATIONS:
- Provide detailed written explanations with definitions
- Include bullet points, numbered lists, and outlines
- Suggest note-taking strategies and summaries
- Use formal, well-structured language
- Include glossaries and key term lists
- Recommend articles, documentation, and textbooks
- Provide written exercises and essay prompts
""",
            'MULTIMODAL': """
MULTIMODAL LEARNER ADAPTATIONS:
- Balance all learning modalities (visual, auditory, kinesthetic, reading)
- Provide multiple representations of each concept
- Include variety in content delivery methods
- Offer choices for how to engage with material
- Mix videos, text, exercises, and discussions
- Allow learner to choose preferred format
"""
        }
        return instructions.get(learning_style, instructions['MULTIMODAL'])

    def _calculate_difficulty(self, user_profile: Dict, performance_history: Dict) -> str:
        """Calculate appropriate difficulty based on user data"""
        skill_level = user_profile.get('skill_level', 50)
        avg_quiz_score = performance_history.get('avg_quiz_score', 0)
        completion_rate = performance_history.get('completion_rate', 50)

        # Weighted score
        weighted_score = (skill_level * 0.4) + (avg_quiz_score * 0.4) + (completion_rate * 0.2)

        if weighted_score >= 80:
            return 'ADVANCED'
        elif weighted_score >= 60:
            return 'INTERMEDIATE'
        elif weighted_score >= 40:
            return 'BEGINNER_PLUS'
        else:
            return 'BEGINNER'

    def _get_module_count(self, user_profile: Dict) -> int:
        """Determine number of modules based on user profile"""
        velocity = user_profile.get('learning_velocity', 1.0)
        if velocity > 1.3:
            return 5  # Fast learner - more comprehensive
        elif velocity < 0.7:
            return 3  # Slower pace - fewer but deeper modules
        return 4  # Standard

    def _get_starting_difficulty(self, performance_history: Dict) -> str:
        """Determine starting difficulty"""
        avg_score = performance_history.get('avg_quiz_score', 50)
        if avg_score >= 80:
            return 'INTERMEDIATE'
        elif avg_score >= 60:
            return 'BEGINNER_PLUS'
        return 'BEGINNER'

    def _get_target_difficulty(self, performance_history: Dict) -> str:
        """Determine target difficulty by end of course"""
        avg_score = performance_history.get('avg_quiz_score', 50)
        if avg_score >= 70:
            return 'ADVANCED'
        elif avg_score >= 50:
            return 'INTERMEDIATE'
        return 'BEGINNER_PLUS'

    # ==================== PERSONALIZED COURSE GENERATION ====================

    def generate_personalized_course(
        self,
        topic: str,
        user_profile: Dict,
        performance_history: Dict,
        weeks: int = 8,
        force_regenerate: bool = False
    ) -> Dict:
        """
        Generate a course tailored to user's learning style and performance.

        Args:
            topic: Course topic
            user_profile: User's learning profile (style, velocity, skill level)
            performance_history: Quiz scores, weak areas, strong areas
            weeks: Target course duration in weeks
            force_regenerate: Skip cache

        Returns:
            Generated course structure
        """
        learning_style = user_profile.get('learning_style', 'MULTIMODAL')
        difficulty = self._calculate_difficulty(user_profile, performance_history)

        # Check cache first
        cache_key = self.cache_service.generate_cache_key(
            'COURSE',
            topic=topic,
            learning_style=learning_style,
            difficulty=difficulty,
            skill_level=user_profile.get('skill_level', 50),
            weeks=weeks
        )

        if not force_regenerate:
            cached = self.cache_service.get_cached_content(cache_key)
            if cached:
                print(f"Using cached course for {topic}")
                return cached

        # Build comprehensive prompt
        prompt = f"""
ROLE: You are an expert instructional designer creating personalized educational content.

TASK: Create a comprehensive course on "{topic}" personalized for this learner.

LEARNER PROFILE:
- Learning Style: {learning_style}
- VARK Scores: Visual={user_profile.get('visual', 50)}, Auditory={user_profile.get('auditory', 50)}, Reading/Writing={user_profile.get('reading_writing', 50)}, Kinesthetic={user_profile.get('kinesthetic', 50)}
- Current Skill Level: {user_profile.get('skill_level', 50)}/100
- Learning Velocity: {user_profile.get('learning_velocity', 1.0)} (1.0 = average, >1 = fast learner, <1 = thorough learner)
- Preferred Session Duration: {user_profile.get('preferred_duration', 30)} minutes

PERFORMANCE HISTORY:
- Average Quiz Score: {performance_history.get('avg_quiz_score', 0):.1f}%
- Strong Areas: {', '.join(performance_history.get('strong_areas', ['None identified']))}
- Areas Needing Improvement: {', '.join(performance_history.get('weak_areas', ['None identified']))}
- Course Completion Rate: {performance_history.get('completion_rate', 0):.1f}%

{self._get_learning_style_instructions(learning_style)}

DIFFICULTY CALIBRATION:
- Starting Difficulty: {self._get_starting_difficulty(performance_history)}
- Target Difficulty: {self._get_target_difficulty(performance_history)}
- Calculated Overall Level: {difficulty}

COURSE STRUCTURE REQUIREMENTS:
1. Create {self._get_module_count(user_profile)} modules with 2-4 lessons each
2. Target duration: {weeks} weeks
3. Each lesson should be {user_profile.get('preferred_duration', 30)} minutes

4. For each lesson, include:
   - Main content adapted to {learning_style} learning style (400-600 words)
   - A "video_search_term" for finding relevant YouTube videos
   - An assignment appropriate for the learner's level
   - 2-3 quiz questions testing the concepts
   - Interactive elements for hands-on practice

5. Incorporate spaced review of weak areas: {', '.join(performance_history.get('weak_areas', []))}

6. Progressive difficulty curve from {self._get_starting_difficulty(performance_history)} to {self._get_target_difficulty(performance_history)}

OUTPUT FORMAT (JSON only):
{{
    "title": "Engaging, descriptive course title",
    "description": "2-3 sentence course description highlighting personalization",
    "personalization_notes": "Explanation of how this course is adapted for the learner",
    "target_audience": "Description of who this course is for",
    "difficulty": "{difficulty}",
    "estimated_hours": {weeks * 5},
    "objectives": ["Learning objective 1", "Learning objective 2", "Learning objective 3"],
    "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
    "modules": [
        {{
            "title": "Module 1: Introduction and Foundations",
            "description": "Module overview",
            "order": 1,
            "estimated_hours": number,
            "learning_objectives": ["Module objective 1", "Module objective 2"],
            "lessons": [
                {{
                    "title": "Lesson Title",
                    "order": 1,
                    "duration_minutes": {user_profile.get('preferred_duration', 30)},
                    "content": "Detailed lesson content adapted for {learning_style} learners. Use appropriate formatting, examples, and explanations. This should be 400-600 words of educational content.",
                    "video_search_term": "specific YouTube search query for this lesson's topic",
                    "learning_style_elements": {{
                        "visual": "Diagram or visual description if applicable",
                        "auditory": "Discussion points or verbal explanation tips",
                        "kinesthetic": "Hands-on activity or exercise",
                        "reading_writing": "Additional reading or note-taking suggestion"
                    }},
                    "code_example": "Complete, working code example with comments if applicable, otherwise null",
                    "assignment": {{
                        "title": "Assignment title",
                        "description": "Clear assignment instructions",
                        "difficulty": "EASY|MEDIUM|HARD",
                        "estimated_minutes": 15,
                        "deliverables": ["What to submit"],
                        "hints": ["Helpful hint 1", "Helpful hint 2"]
                    }},
                    "quiz_questions": [
                        {{
                            "question": "Quiz question text",
                            "options": ["Option A", "Option B", "Option C", "Option D"],
                            "correct_answer": 0,
                            "explanation": "Why this answer is correct",
                            "difficulty": "EASY|MEDIUM|HARD",
                            "concept_tested": "The specific concept this question tests"
                        }}
                    ],
                    "interactive_element": "Description of interactive exercise or activity",
                    "key_takeaways": ["Key point 1", "Key point 2", "Key point 3"],
                    "reinforcement_topics": ["Topic from weak areas to reinforce if applicable"]
                }}
            ]
        }}
    ],
    "tags": ["tag1", "tag2", "tag3"],
    "difficulty_progression": ["EASY", "EASY", "MEDIUM", "MEDIUM", "HARD"]
}}

CRITICAL: Respond with ONLY the JSON object. No markdown, no explanations, just valid JSON.
"""

        try:
            # Call Gemini
            response = self.gemini_service.model.generate_content(prompt)

            if response.text:
                course = self._parse_json_response(response.text, topic, difficulty)

                # Add YouTube videos to lessons
                course = self._enrich_with_youtube_videos(course)

                # Cache the result
                self.cache_service.cache_content(
                    cache_key=cache_key,
                    content=course,
                    content_type='COURSE',
                    topic=topic,
                    difficulty=difficulty,
                    learning_style=learning_style
                )

                return course

        except Exception as e:
            print(f"Error generating personalized course: {str(e)}")

        # Fallback
        return self._get_fallback_course(topic, difficulty, learning_style)

    def _enrich_with_youtube_videos(self, course: Dict) -> Dict:
        """Add YouTube video URLs to lessons"""
        try:
            for module in course.get('modules', []):
                for lesson in module.get('lessons', []):
                    search_term = lesson.get('video_search_term', lesson.get('title', ''))
                    if search_term:
                        videos = self.youtube_service.search_videos(
                            f"{search_term} tutorial",
                            max_results=1
                        )
                        if videos:
                            lesson['video_url'] = videos[0].get('url')
                            lesson['video_id'] = videos[0].get('id')
                            lesson['video_thumbnail'] = videos[0].get('thumbnail_url')
        except Exception as e:
            print(f"Error enriching with YouTube videos: {str(e)}")

        return course

    # ==================== ADAPTIVE QUIZ GENERATION ====================

    def generate_adaptive_quiz(
        self,
        topic: str,
        user_performance: Dict,
        learning_style: str,
        question_count: int = 10,
        force_regenerate: bool = False
    ) -> Dict:
        """
        Generate quiz that adapts to user's performance and learning style.

        Args:
            topic: Quiz topic
            user_performance: Performance metrics and weak areas
            learning_style: User's dominant learning style
            question_count: Number of questions
            force_regenerate: Skip cache

        Returns:
            Generated quiz
        """
        # Calculate difficulty distribution based on performance
        avg_score = user_performance.get('recent_avg_score', 50)
        weak_areas = user_performance.get('weak_areas', [])

        if avg_score >= 80:
            # High performer - more hard questions
            difficulty_dist = {'easy': 2, 'medium': 3, 'hard': 5}
        elif avg_score >= 60:
            # Average - balanced
            difficulty_dist = {'easy': 3, 'medium': 4, 'hard': 3}
        else:
            # Struggling - more easy questions for confidence
            difficulty_dist = {'easy': 5, 'medium': 3, 'hard': 2}

        # Scale to question count
        total = sum(difficulty_dist.values())
        difficulty_dist = {
            k: max(1, int(v / total * question_count))
            for k, v in difficulty_dist.items()
        }

        # Check cache
        cache_key = self.cache_service.generate_cache_key(
            'QUIZ',
            topic=topic,
            learning_style=learning_style,
            question_count=question_count,
            avg_score=int(avg_score / 10) * 10  # Round to nearest 10 for better cache hits
        )

        if not force_regenerate:
            cached = self.cache_service.get_cached_content(cache_key)
            if cached:
                return cached

        # Build prompt
        prompt = f"""
ROLE: You are an expert educational assessment designer.

TASK: Create an adaptive quiz on "{topic}" that assesses understanding while reinforcing learning.

LEARNER CONTEXT:
- Learning Style: {learning_style}
- Recent Performance: {avg_score:.1f}%
- Topics to Reinforce: {', '.join(weak_areas) if weak_areas else 'General concepts'}
- Strengths: {', '.join(user_performance.get('strong_areas', ['Fundamentals']))}

DIFFICULTY DISTRIBUTION:
- Easy questions: {difficulty_dist['easy']} (build confidence, verify basics)
- Medium questions: {difficulty_dist['medium']} (standard assessment)
- Hard questions: {difficulty_dist['hard']} (challenge and extend)

ADAPTIVE QUIZ DESIGN PRINCIPLES:
1. Start with a medium question to gauge current level
2. Include MORE questions on weak areas: {', '.join(weak_areas) if weak_areas else 'N/A'}
3. Adapt question format to {learning_style} learning style:
   - VISUAL: Include scenario descriptions, diagram-based questions
   - AUDITORY: Include dialogue scenarios, verbal reasoning
   - KINESTHETIC: Include practical application, "what would you do" scenarios
   - READING_WRITING: Include definition questions, text analysis

4. Each question should:
   - Target a specific concept
   - Include helpful explanation regardless of answer
   - Have clear, unambiguous options

QUESTION TYPE DISTRIBUTION:
- Conceptual understanding: 40%
- Practical application: 30%
- Analysis/problem-solving: 20%
- Synthesis/connection: 10%

OUTPUT FORMAT (JSON only):
{{
    "title": "{topic} Assessment",
    "description": "Personalized quiz adapted for {learning_style} learners",
    "topic": "{topic}",
    "total_questions": {question_count},
    "time_limit_minutes": {question_count * 2},
    "passing_score": {max(60, min(80, int(avg_score - 10)))},
    "difficulty_distribution": {json.dumps(difficulty_dist)},
    "questions": [
        {{
            "id": 1,
            "question_text": "Question adapted for {learning_style} style",
            "question_type": "MULTIPLE_CHOICE",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Detailed explanation for learning",
            "difficulty": "EASY|MEDIUM|HARD",
            "concept_tested": "specific concept this tests",
            "targets_weak_area": true|false,
            "learning_style_note": "How this question suits {learning_style} learners",
            "if_wrong_review": "Topic to review if answered incorrectly"
        }}
    ],
    "recommended_actions": {{
        "if_score_below_50": "Recommendation for struggling learners",
        "if_score_50_to_80": "Recommendation for average performance",
        "if_score_above_80": "Recommendation for high performers"
    }}
}}

Generate exactly {question_count} questions with the specified difficulty distribution.
RESPOND WITH ONLY THE JSON OBJECT.
"""

        try:
            response = self.gemini_service.model.generate_content(prompt)

            if response.text:
                quiz = self._parse_json_response(response.text, topic, 'quiz')

                # Cache result
                self.cache_service.cache_content(
                    cache_key=cache_key,
                    content=quiz,
                    content_type='QUIZ',
                    topic=topic,
                    learning_style=learning_style
                )

                return quiz

        except Exception as e:
            print(f"Error generating adaptive quiz: {str(e)}")

        return self._get_fallback_quiz(topic, question_count)

    # ==================== PERSONALIZED ASSIGNMENT GENERATION ====================

    def generate_personalized_assignment(
        self,
        topic: str,
        lesson_content: str,
        user_profile: Dict,
        performance_history: Dict,
        force_regenerate: bool = False
    ) -> Dict:
        """
        Generate assignment tailored to skill level and learning style.

        Args:
            topic: Assignment topic
            lesson_content: Content from the lesson
            user_profile: User's learning profile
            performance_history: Performance metrics

        Returns:
            Generated assignment
        """
        skill_level = user_profile.get('skill_level', 50)
        learning_style = user_profile.get('learning_style', 'MULTIMODAL')

        # Determine difficulty
        if skill_level >= 75:
            difficulty = 'HARD'
        elif skill_level >= 50:
            difficulty = 'MEDIUM'
        else:
            difficulty = 'EASY'

        # Check cache
        cache_key = self.cache_service.generate_cache_key(
            'ASSIGNMENT',
            topic=topic,
            learning_style=learning_style,
            difficulty=difficulty
        )

        if not force_regenerate:
            cached = self.cache_service.get_cached_content(cache_key)
            if cached:
                return cached

        prompt = f"""
ROLE: You are an expert educational content creator specializing in practical assessments.

TASK: Create a personalized assignment for "{topic}".

LESSON CONTEXT (summarized):
{lesson_content[:1500] if lesson_content else 'General topic content'}

LEARNER PROFILE:
- Skill Level: {skill_level}/100
- Learning Style: {learning_style}
- Difficulty Level: {difficulty}
- Weak Areas: {', '.join(performance_history.get('weak_areas', ['General concepts']))}
- Strong Areas: {', '.join(performance_history.get('strong_areas', ['Fundamentals']))}

DIFFICULTY CALIBRATION for {difficulty}:
- EASY: Clear step-by-step instructions, templates provided, scaffolded learning
- MEDIUM: General guidance, some scaffolding, room for creativity
- HARD: Open-ended, minimal scaffolding, requires independent research

LEARNING STYLE ADAPTATION for {learning_style}:
- VISUAL: Include diagram creation, visual presentation elements
- AUDITORY: Include verbal explanation component, presentation element
- KINESTHETIC: Focus on hands-on building and implementation
- READING_WRITING: Include documentation and written analysis

OUTPUT FORMAT (JSON only):
{{
    "title": "Assignment Title",
    "description": "Brief overview (2-3 sentences)",
    "topic": "{topic}",
    "difficulty": "{difficulty}",
    "estimated_time_minutes": {30 if difficulty == 'EASY' else 45 if difficulty == 'MEDIUM' else 60},
    "submission_type": "CODE|TEXT|FILE|PRESENTATION",
    "learning_objectives": [
        "What learner will demonstrate 1",
        "What learner will demonstrate 2"
    ],
    "instructions": {{
        "overview": "What the student will create/accomplish",
        "preparation": "What to prepare before starting",
        "steps": [
            {{
                "step_number": 1,
                "title": "Step title",
                "description": "Detailed instructions for this step",
                "hints": ["Helpful hint if needed"],
                "checkpoint": "How to verify this step is complete"
            }}
        ],
        "deliverables": ["Specific deliverable 1", "Specific deliverable 2"]
    }},
    "rubric": [
        {{
            "criterion": "Criterion name",
            "description": "What is being assessed",
            "weight": 25,
            "levels": {{
                "excellent": "Description (90-100%)",
                "good": "Description (70-89%)",
                "satisfactory": "Description (50-69%)",
                "needs_improvement": "Description (below 50%)"
            }}
        }}
    ],
    "resources": [
        {{
            "title": "Resource name",
            "type": "DOCUMENTATION|TUTORIAL|EXAMPLE|TOOL",
            "description": "How this resource helps"
        }}
    ],
    "starter_code": "Starter code template if applicable, otherwise null",
    "solution_hints": ["Hint for struggling students"],
    "extensions": ["Challenge extension for advanced students"],
    "support_options": ["Simplified version option", "Additional scaffolding option"]
}}

RESPOND WITH ONLY THE JSON OBJECT.
"""

        try:
            response = self.gemini_service.model.generate_content(prompt)

            if response.text:
                assignment = self._parse_json_response(response.text, topic, 'assignment')

                # Cache result
                self.cache_service.cache_content(
                    cache_key=cache_key,
                    content=assignment,
                    content_type='ASSIGNMENT',
                    topic=topic,
                    difficulty=difficulty,
                    learning_style=learning_style
                )

                return assignment

        except Exception as e:
            print(f"Error generating assignment: {str(e)}")

        return self._get_fallback_assignment(topic, difficulty)

    # ==================== LEARNING PATH GENERATION ====================

    def generate_learning_path(
        self,
        target_skill: str,
        current_level: str,
        learning_style: str,
        weeks: int = 12,
        user_profile: Dict = None
    ) -> Dict:
        """Generate personalized learning path"""

        prompt = f"""
ROLE: You are an expert learning path designer.

TASK: Create a {weeks}-week personalized learning path to master "{target_skill}".

LEARNER CONTEXT:
- Current Level: {current_level}
- Learning Style: {learning_style}
- Available Time: {weeks} weeks

OUTPUT FORMAT (JSON only):
{{
    "title": "Path to {target_skill} Mastery",
    "description": "Personalized learning journey",
    "target_skill": "{target_skill}",
    "duration_weeks": {weeks},
    "total_estimated_hours": {weeks * 10},
    "milestones": [
        {{
            "id": 1,
            "title": "Milestone title",
            "week_start": 1,
            "week_end": 3,
            "description": "What you'll achieve",
            "skills_gained": ["skill 1", "skill 2"],
            "courses_or_topics": ["course/topic 1", "course/topic 2"],
            "assessment": "How mastery is verified",
            "success_criteria": ["criterion 1", "criterion 2"]
        }}
    ],
    "weekly_breakdown": [
        {{
            "week": 1,
            "focus": "Main focus for this week",
            "topics": ["topic 1", "topic 2"],
            "activities": ["activity 1", "activity 2"],
            "time_hours": 10,
            "learning_style_tips": "Tips for {learning_style} learners"
        }}
    ],
    "recommended_resources": [
        {{
            "title": "Resource name",
            "type": "COURSE|BOOK|PROJECT|TUTORIAL",
            "description": "Why this resource"
        }}
    ],
    "success_metrics": ["How to measure progress"],
    "potential_challenges": ["Challenge and how to overcome"]
}}

RESPOND WITH ONLY THE JSON OBJECT.
"""

        try:
            response = self.gemini_service.model.generate_content(prompt)

            if response.text:
                return self._parse_json_response(response.text, target_skill, 'learning_path')

        except Exception as e:
            print(f"Error generating learning path: {str(e)}")

        return self._get_fallback_learning_path(target_skill, weeks)

    # ==================== HELPER METHODS ====================

    def _parse_json_response(self, response_text: str, topic: str, content_type: str) -> Dict:
        """Robustly parse JSON from AI response"""
        try:
            clean_text = response_text.strip()

            # Remove markdown code blocks
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0]
            elif "```" in clean_text:
                parts = clean_text.split("```")
                if len(parts) >= 2:
                    clean_text = parts[1]

            # Find JSON object
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')

            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx + 1]

            return json.loads(clean_text)

        except Exception as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Raw text (first 500 chars): {response_text[:500]}")

            # Return appropriate fallback
            if content_type == 'quiz':
                return self._get_fallback_quiz(topic, 5)
            elif content_type == 'assignment':
                return self._get_fallback_assignment(topic, 'MEDIUM')
            elif content_type == 'learning_path':
                return self._get_fallback_learning_path(topic, 12)
            else:
                return self._get_fallback_course(topic, 'INTERMEDIATE', 'MULTIMODAL')

    def _get_fallback_course(self, topic: str, difficulty: str, learning_style: str) -> Dict:
        """Generate fallback course structure"""
        return {
            "title": f"Introduction to {topic}",
            "description": f"A comprehensive course on {topic} designed for your learning style.",
            "personalization_notes": f"This course is adapted for {learning_style} learners.",
            "difficulty": difficulty,
            "estimated_hours": 20,
            "objectives": [
                f"Understand the fundamentals of {topic}",
                f"Apply {topic} concepts in practical scenarios",
                "Build real-world projects"
            ],
            "modules": [
                {
                    "title": f"Module 1: {topic} Fundamentals",
                    "order": 1,
                    "lessons": [
                        {
                            "title": f"Introduction to {topic}",
                            "order": 1,
                            "duration_minutes": 30,
                            "content": f"Welcome to your journey learning {topic}. This lesson covers the foundational concepts you need to get started.",
                            "video_search_term": f"{topic} introduction tutorial for beginners"
                        }
                    ]
                }
            ],
            "tags": [topic, "beginner-friendly", "self-paced"]
        }

    def _get_fallback_quiz(self, topic: str, question_count: int) -> Dict:
        """Generate fallback quiz"""
        questions = []
        for i in range(question_count):
            questions.append({
                "id": i + 1,
                "question_text": f"What is a fundamental concept in {topic}?",
                "options": [
                    "Core principle and foundation",
                    "Advanced technique",
                    "Optional feature",
                    "Unrelated concept"
                ],
                "correct_answer": 0,
                "explanation": f"Understanding core principles is essential for mastering {topic}.",
                "difficulty": "MEDIUM",
                "concept_tested": "fundamentals"
            })

        return {
            "title": f"{topic} Assessment",
            "topic": topic,
            "total_questions": question_count,
            "passing_score": 70,
            "questions": questions
        }

    def _get_fallback_assignment(self, topic: str, difficulty: str) -> Dict:
        """Generate fallback assignment"""
        return {
            "title": f"{topic} Practical Exercise",
            "description": f"Apply your knowledge of {topic} in a practical exercise.",
            "difficulty": difficulty,
            "estimated_time_minutes": 45,
            "submission_type": "TEXT",
            "instructions": {
                "overview": f"Demonstrate your understanding of {topic}",
                "steps": [
                    {
                        "step_number": 1,
                        "title": "Research",
                        "description": f"Review the key concepts of {topic}"
                    },
                    {
                        "step_number": 2,
                        "title": "Apply",
                        "description": "Apply the concepts to solve a problem"
                    }
                ],
                "deliverables": ["Written explanation", "Example demonstration"]
            }
        }

    def _get_fallback_learning_path(self, target_skill: str, weeks: int) -> Dict:
        """Generate fallback learning path"""
        return {
            "title": f"Path to {target_skill} Mastery",
            "target_skill": target_skill,
            "duration_weeks": weeks,
            "milestones": [
                {
                    "id": 1,
                    "title": "Foundation",
                    "week_start": 1,
                    "week_end": weeks // 3,
                    "description": f"Build strong foundations in {target_skill}"
                },
                {
                    "id": 2,
                    "title": "Application",
                    "week_start": weeks // 3 + 1,
                    "week_end": 2 * weeks // 3,
                    "description": "Apply concepts in practical projects"
                },
                {
                    "id": 3,
                    "title": "Mastery",
                    "week_start": 2 * weeks // 3 + 1,
                    "week_end": weeks,
                    "description": "Achieve mastery through advanced projects"
                }
            ]
        }


# Singleton instance
_ai_content_service = None

def get_ai_content_service() -> AIContentGenerationService:
    """Get the singleton AI content service instance"""
    global _ai_content_service
    if _ai_content_service is None:
        _ai_content_service = AIContentGenerationService()
    return _ai_content_service
