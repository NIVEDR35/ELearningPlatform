import google.generativeai as genai
from typing import Dict, List, Optional, Any
import json
import os

class GeminiService:
    """Service for Gemini AI integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Use new API key with better quota (Default Gemini API Key)
        self.api_key = api_key or 'AIzaSyCl1zPkJHkPT8MIZAuUafCn-30Gt-fISaE'
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use free, fast model with better quota limits
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
            print("Warning: Gemini API key not configured. Using fallback responses.")
    
    def generate_course_recommendations(
        self,
        learning_style: str,
        completed_courses: List[str],
        user_goal: str,
        experience_level: str
    ) -> Dict:
        """Generate personalized course recommendations"""
        
        prompt = f"""Based on the following student profile, recommend 5 courses:
- Learning Style: {learning_style}
- Completed Courses: {', '.join(completed_courses) if completed_courses else 'None'}
- Goal: {user_goal}
- Experience Level: {experience_level}

Provide recommendations with reasoning. Format as JSON:
{{
  "recommendations": [
    {{
      "title": "Course Title",
      "reasoning": "Why this course is recommended",
      "learningStyleMatch": 85,
      "difficulty": "INTERMEDIATE",
      "estimatedDuration": 40
    }}
  ]
}}"""
        
        return self._call_gemini(prompt)
    
    def generate_learning_path(
        self,
        target_skill: str,
        current_level: str,
        learning_style: str,
        time_available_weeks: int
    ) -> Dict:
        """Generate personalized learning path"""
        
        prompt = f"""Create a personalized {time_available_weeks}-week learning path for someone who wants to learn {target_skill}.
Current level: {current_level}
Learning style: {learning_style}

Provide a week-by-week breakdown with specific topics, resources, and milestones.
Format as JSON:
{{
  "weeks": [
    {{
      "week": 1,
      "topics": ["Topic 1", "Topic 2"],
      "resources": ["Resource 1", "Resource 2"],
      "milestone": "Complete fundamentals",
      "learningStyleTips": "Tips for {learning_style} learners"
    }}
  ]
}}"""
        
        return self._call_gemini(prompt)
    
    def adapt_content_for_learning_style(
        self,
        content: str,
        learning_style: str
    ) -> str:
        """Adapt content for specific learning style"""
        
        style_instructions = {
            'VISUAL': 'Add visual descriptions, suggest diagrams, use spatial metaphors',
            'AUDITORY': 'Add discussion points, suggest audio resources, use conversational tone',
            'KINESTHETIC': 'Add hands-on exercises, practical examples, interactive elements',
            'READING_WRITING': 'Add detailed explanations, suggest reading materials, include note-taking tips'
        }
        
        instruction = style_instructions.get(learning_style, 'Make it engaging')
        
        prompt = f"""Adapt the following educational content for a {learning_style} learner.
{instruction}:

{content}

Provide the adapted content in a clear, engaging format."""
        
        response = self._call_gemini(prompt)
        return response.get('text', content) if isinstance(response, dict) else content
    
    def generate_personalized_explanation(
        self,
        concept: str,
        learning_style: str,
        attempt_count: int,
        previous_errors: str
    ) -> str:
        """Generate personalized explanation for struggling students"""
        
        prompt = f"""A student is struggling with the concept of '{concept}' (attempt #{attempt_count}).
Their learning style is {learning_style}.
Previous errors: {previous_errors}

Provide a clear, personalized explanation using their preferred learning style.
Include:
1. Simple analogy
2. Step-by-step breakdown
3. Common pitfalls to avoid
4. Practice suggestions

Format as clear, encouraging text."""
        
        response = self._call_gemini(prompt)
        return response.get('text', f"Let's break down {concept} step by step...") if isinstance(response, dict) else str(response)
    
    def predict_progress_and_suggest_interventions(
        self,
        course_name: str,
        current_progress: float,
        days_elapsed: int,
        target_days: int,
        engagement_pattern: str
    ) -> Dict:
        """Predict course completion and suggest interventions"""
        
        prompt = f"""Analyze this student's progress:
- Course: {course_name}
- Progress: {current_progress}% complete after {days_elapsed} days (target: {target_days} days)
- Engagement pattern: {engagement_pattern}

Predict likelihood of completion and suggest specific interventions if needed.
Format as JSON:
{{
  "completionProbability": 75,
  "riskLevel": "medium",
  "interventions": ["Suggestion 1", "Suggestion 2"],
  "reasoning": "Analysis of progress"
}}"""
        
        return self._call_gemini(prompt)
    
    def generate_adaptive_quiz(
        self,
        topic: str,
        difficulty: str,
        learning_style: str,
        question_count: int = 5
    ) -> Dict:
        """Generate adaptive quiz questions"""
        
        prompt = f"""Generate {question_count} {difficulty}-level quiz questions about '{topic}' optimized for {learning_style} learners.

Format as JSON:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctAnswer": 0,
      "explanation": "Why this is correct",
      "learningStyleHint": "Hint for {learning_style} learners"
    }}
  ]
}}"""
        
        return self._call_gemini(prompt)
    
    def generate_course_content(self, topic: str, difficulty: str = "Intermediate", weeks: int = 8, goal: str = "") -> Dict[str, Any]:
        """Generate comprehensive course content using Gemini"""
        if not self.model:
            return self._get_fallback_course(topic, difficulty)
            
        prompt = f"""
        IMPORTANT: You must respond with ONLY valid JSON. No additional text, explanations, or markdown formatting.
        
        Create a comprehensive course structure for the topic '{topic}' at {difficulty} difficulty level.
        Target Duration: {weeks} weeks.
        User Goal: {goal}
        
        Return ONLY the JSON response with this exact structure:
        
        {{
            "title": "engaging and descriptive course title",
            "description": "2-3 sentence course description",
            "objectives": ["Objective 1", "Objective 2", "Objective 3"],
            "modules": [
                {{
                    "title": "Module 1: Fundamentals",
                    "topics": ["Topic 1", "Topic 2"],
                    "lessons": [
                        {{
                            "title": "Lesson Title",
                            "content": "Detailed lesson content explaining the concept with examples and explanations (500-800 words). Include markdown formatting for better readability.",
                            "video_search_term": "specific search query for finding the best youtube video for this lesson",
                            "duration_minutes": 15,
                            "assignment": "Hands-on assignment or exercise for students to practice. Be specific with requirements and expected outcomes.",
                            "code_example": "If applicable, provide a complete, working code example with comments explaining each part.",
                            "interactive_element": "Description of an interactive exercise, challenge, or activity students can do to reinforce learning.",
                            "quiz_questions": [
                                {{
                                    "question": "Question text?",
                                    "options": ["Option A", "Option B", "Option C", "Option D"],
                                    "correct_answer": 0,
                                    "explanation": "Why this answer is correct"
                                }}
                            ],
                            "document_reference": "Suggested reading material, documentation, or article title that students can explore for deeper understanding."
                        }}
                    ]
                }}
            ],
            "prerequisites": ["prerequisite 1", "prerequisite 2"],
            "estimated_hours": {weeks * 5},
            "total_duration_hours": {weeks * 5},
            "difficulty": "{difficulty.upper()}",
            "tags": ["tag1", "tag2", "tag3"]
        }}
        
        Generate {max(3, weeks // 2)} modules with 2-3 lessons each. Each lesson MUST include:
        - Rich, detailed content (Reading/Writing learners)
        - Practical assignment (Kinesthetic learners)
        - Code examples when relevant (Kinesthetic learners)
        - Interactive elements (Kinesthetic learners)
        - 2-3 quiz questions (All learning styles)
        - Document references (Reading/Writing learners)
        
        Make content educational, practical, and aligned with the user's goal.
        RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT.
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return self._parse_json_response(response.text, topic, difficulty)
            return self._get_fallback_course(topic, difficulty)
        except Exception as e:
            print(f"Error generating course: {str(e)}")
            return self._get_fallback_course(topic, difficulty)

    def generate_test(self, topic: str, difficulty: str = "Intermediate", num_questions: int = 5) -> Dict[str, Any]:
        """Generate a quiz/test using Gemini"""
        if not self.model:
            return self._get_fallback_test(topic, difficulty, num_questions)

        # Better prompt for higher quality questions
        prompt = f"""
        IMPORTANT: You must respond with ONLY valid JSON. No additional text, explanations, or markdown formatting.

        Create a professional {num_questions}-question multiple choice assessment test on '{topic}' at {difficulty} difficulty level.

        REQUIREMENTS:
        1. Questions must be clear, specific, and test actual knowledge of {topic}
        2. All 4 options must be plausible - avoid obviously wrong answers
        3. Questions should cover different aspects/concepts of {topic}
        4. For {difficulty} level:
           - beginner: Focus on definitions, basic concepts, simple applications
           - intermediate: Focus on understanding, comparisons, practical usage
           - advanced: Focus on edge cases, best practices, complex scenarios
        5. Each question must have exactly 4 options
        6. Include a helpful explanation for the correct answer

        Return ONLY this JSON structure:

        {{
            "title": "{topic} Assessment",
            "description": "Test your understanding of {topic} concepts and applications",
            "questions": [
                {{
                    "id": 1,
                    "question_text": "Clear and specific question about {topic}?",
                    "options": ["Option A - plausible answer", "Option B - plausible answer", "Option C - plausible answer", "Option D - plausible answer"],
                    "correct_answer": 0,
                    "explanation": "Clear explanation of why this is the correct answer and why others are wrong"
                }}
            ]
        }}

        'correct_answer' must be the 0-based index (0, 1, 2, or 3) of the correct option.
        RESPOND WITH ONLY THE JSON OBJECT.
        """

        try:
            response = self.model.generate_content(prompt)
            if response.text:
                test_data = self._parse_json_response(response.text, topic, difficulty, is_test=True)

                # Normalize question fields for consistency
                if 'questions' in test_data:
                    for q in test_data['questions']:
                        # Handle both correct_option and correct_answer field names
                        if 'correct_option' in q and 'correct_answer' not in q:
                            q['correct_answer'] = q['correct_option']
                        elif 'correct_answer' not in q:
                            q['correct_answer'] = 0  # Default to first option

                # Ensure required fields are present
                test_data['difficulty'] = difficulty.capitalize()
                test_data['topic'] = topic
                test_data['passing_score'] = 70
                return test_data
            return self._get_fallback_test(topic, difficulty, num_questions)
        except Exception as e:
            print(f"Error generating test: {str(e)}")
            return self._get_fallback_test(topic, difficulty, num_questions)

    def _parse_json_response(self, response_text: str, topic: str, difficulty: str, is_test: bool = False) -> Dict[str, Any]:
        """Robustly parse JSON response from AI"""
        try:
            # Clean response text
            clean_text = response_text.strip()
            
            # Remove markdown code blocks
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0]
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0]
                
            # Extract JSON object
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]
                
            return json.loads(clean_text)
        except Exception as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Raw text: {response_text}")
            if is_test:
                return self._get_fallback_test(topic, difficulty, 5)
            return self._get_fallback_course(topic, difficulty)

    def _get_fallback_course(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate fallback course content"""
        return {
            "title": f"Introduction to {topic}",
            "description": f"A comprehensive guide to mastering {topic} concepts.",
            "objectives": [
                f"Understand the basics of {topic}",
                f"Apply {topic} concepts in real-world scenarios",
                "Build a strong foundation for advanced learning"
            ],
            "modules": [
                {
                    "title": "Module 1: Basics",
                    "topics": ["Introduction", "Setup", "Basic Concepts"],
                    "lessons": [
                        {
                            "title": f"What is {topic}?",
                            "content": f"Introduction to core concepts of {topic}.",
                            "duration_minutes": 15
                        },
                        {
                            "title": "Getting Started",
                            "content": "Setting up your environment and basic syntax.",
                            "duration_minutes": 20
                        }
                    ]
                },
                {
                    "title": "Module 2: Core Concepts",
                    "topics": ["Key Features", "Best Practices", "Examples"],
                    "lessons": [
                        {
                            "title": "Key Features",
                            "content": "Deep dive into important features and patterns.",
                            "duration_minutes": 25
                        },
                        {
                            "title": "Best Practices",
                            "content": "Learning industry standards and coding conventions.",
                            "duration_minutes": 20
                        }
                    ]
                }
            ],
            "prerequisites": ["Basic programming knowledge", "Computer literacy"],
            "estimated_hours": 5,
            "total_duration_hours": 5,
            "difficulty": difficulty.upper(),
            "tags": [topic, "Programming", "Technology"]
        }

    def _get_fallback_test(self, topic: str, difficulty: str, num_questions: int) -> Dict[str, Any]:
        """Generate fallback test content with better quality questions"""
        # Pre-defined question templates for common topics
        question_templates = {
            "python": [
                {"q": "What is the correct way to create a list in Python?", "opts": ["list = []", "list = {}", "list = ()", "list = <>"], "ans": 0, "exp": "Lists in Python are created using square brackets []."},
                {"q": "Which keyword is used to define a function in Python?", "opts": ["def", "function", "func", "define"], "ans": 0, "exp": "The 'def' keyword is used to define functions in Python."},
                {"q": "What does 'len()' function return?", "opts": ["The length/size of an object", "The last element", "The first element", "The type of object"], "ans": 0, "exp": "len() returns the number of items in an object."},
                {"q": "Which of the following is a mutable data type?", "opts": ["List", "Tuple", "String", "Integer"], "ans": 0, "exp": "Lists are mutable, meaning their contents can be changed after creation."},
                {"q": "What is the output of print(2 ** 3)?", "opts": ["8", "6", "9", "5"], "ans": 0, "exp": "** is the exponentiation operator, so 2^3 = 8."},
            ],
            "javascript": [
                {"q": "Which keyword declares a block-scoped variable?", "opts": ["let", "var", "const", "Both let and const"], "ans": 3, "exp": "Both 'let' and 'const' are block-scoped, unlike 'var'."},
                {"q": "What does '===' operator check?", "opts": ["Value and type equality", "Only value equality", "Reference equality", "None of the above"], "ans": 0, "exp": "=== checks both value and type (strict equality)."},
                {"q": "Which method adds an element to the end of an array?", "opts": ["push()", "pop()", "shift()", "unshift()"], "ans": 0, "exp": "push() adds elements to the end of an array."},
                {"q": "What is a closure in JavaScript?", "opts": ["A function with access to its outer scope", "A way to close the browser", "A loop structure", "An error type"], "ans": 0, "exp": "A closure is a function that retains access to variables from its outer scope."},
                {"q": "Which is NOT a JavaScript data type?", "opts": ["float", "string", "boolean", "undefined"], "ans": 0, "exp": "JavaScript uses 'number' for all numeric values, not 'float'."},
            ],
            "default": [
                {"q": f"What is the primary purpose of {topic}?", "opts": [f"To solve problems in {topic} domain", "For entertainment only", "It has no real purpose", "Only for documentation"], "ans": 0, "exp": f"{topic} is designed to solve real-world problems in its domain."},
                {"q": f"Which is a best practice when working with {topic}?", "opts": ["Follow established conventions", "Ignore documentation", "Never test your work", "Avoid learning fundamentals"], "ans": 0, "exp": "Following established conventions ensures maintainable and readable code."},
                {"q": f"What should you do before starting with {topic}?", "opts": ["Understand the basics first", "Skip to advanced topics", "Ignore prerequisites", "Never read documentation"], "ans": 0, "exp": "Understanding basics builds a strong foundation for advanced concepts."},
                {"q": f"How can you improve your skills in {topic}?", "opts": ["Practice regularly with exercises", "Only read without practicing", "Avoid challenging problems", "Never ask for help"], "ans": 0, "exp": "Regular practice is the most effective way to improve programming skills."},
                {"q": f"What is important when debugging in {topic}?", "opts": ["Systematic problem isolation", "Random code changes", "Ignoring error messages", "Deleting all code"], "ans": 0, "exp": "Systematic debugging helps identify and fix issues efficiently."},
            ]
        }

        # Get topic-specific questions or use default
        topic_lower = topic.lower()
        if "python" in topic_lower:
            templates = question_templates["python"]
        elif "javascript" in topic_lower or "js" in topic_lower:
            templates = question_templates["javascript"]
        else:
            templates = question_templates["default"]

        questions = []
        for i in range(min(num_questions, len(templates))):
            t = templates[i]
            questions.append({
                "id": i + 1,
                "question_text": t["q"],
                "options": t["opts"],
                "correct_answer": t["ans"],
                "explanation": t["exp"]
            })

        # If we need more questions than templates, add generic ones
        for i in range(len(questions), num_questions):
            questions.append({
                "id": i + 1,
                "question_text": f"What is an important concept in {topic}?",
                "options": [
                    "Understanding core fundamentals",
                    "Skipping basic concepts",
                    "Avoiding practice",
                    "Ignoring best practices"
                ],
                "correct_answer": 0,
                "explanation": f"Core fundamentals are essential for mastering {topic}."
            })

        return {
            "title": f"{topic} Assessment",
            "description": f"Test your knowledge of {topic}",
            "difficulty": difficulty.capitalize(),
            "topic": topic,
            "passing_score": 70,
            "questions": questions
        }
    
    def analyze_learning_behavior(
        self,
        behavior_data: Dict
    ) -> Dict:
        """Analyze learning behavior and provide insights"""
        
        behavior_json = json.dumps(behavior_data, indent=2)
        
        prompt = f"""Analyze this student's learning behavior data and provide insights:

{behavior_json}

Identify patterns, strengths, areas for improvement, and personalized recommendations.
Format as JSON:
{{
  "insights": ["Insight 1", "Insight 2"],
  "strengths": ["Strength 1", "Strength 2"],
  "improvements": ["Area 1", "Area 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"]
}}"""
        
        return self._call_gemini(prompt)
    
    def _call_gemini(self, prompt: str) -> Dict:
        """Call Gemini API with error handling"""
        
        if not self.model:
            return self._fallback_response(prompt)
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Try to parse as JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {'text': text}
                
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> Dict:
        """Generate fallback response when API is unavailable"""
        
        if 'recommend' in prompt.lower():
            return {
                "recommendations": [
                    {
                        "title": "Introduction to Programming",
                        "reasoning": "Great starting point for beginners",
                        "learningStyleMatch": 85,
                        "difficulty": "BEGINNER",
                        "estimatedDuration": 30
                    }
                ]
            }
        elif 'learning path' in prompt.lower():
            return {
                "weeks": [
                    {
                        "week": 1,
                        "topics": ["Basics", "Fundamentals"],
                        "resources": ["Online tutorials", "Documentation"],
                        "milestone": "Complete fundamentals",
                        "learningStyleTips": "Practice regularly"
                    }
                ]
            }
        else:
            return {
                'text': 'AI service temporarily unavailable. Using default recommendations.'
            }
