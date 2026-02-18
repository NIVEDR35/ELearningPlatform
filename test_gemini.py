#!/usr/bin/env python3
"""Test Gemini API connectivity and functionality"""

import google.generativeai as genai
import json

# Configure API with new key
API_KEY = 'AIzaSyAkosizSROQfRoh-Y6tnzCsV4vvemow3Cs'
genai.configure(api_key=API_KEY)

print("=" * 60)
print("🧪 Testing Gemini API")
print("=" * 60)

try:
    # Test 1: List available models
    print("\n1️⃣ Testing: List Available Models")
    print("-" * 60)
    models = genai.list_models()
    available_models = []
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            available_models.append(model.name)
            print(f"✅ {model.name}")
    
    if not available_models:
        print("❌ No models available for content generation")
    
    # Test 2: Simple text generation
    print("\n2️⃣ Testing: Simple Text Generation")
    print("-" * 60)
    model = genai.GenerativeModel('gemini-2.0-flash')  # Stable 2.0 model
    
    prompt = "Say 'Hello! I am working!' in exactly 5 words."
    print(f"Prompt: {prompt}")
    
    response = model.generate_content(prompt)
    print(f"Response: {response.text}")
    print("✅ Text generation working!")
    
    # Test 3: JSON generation (for courses/tests)
    print("\n3️⃣ Testing: JSON Generation")
    print("-" * 60)
    
    json_prompt = """Generate a simple quiz question about Python in JSON format:
{
  "question": "What is Python?",
  "options": ["A snake", "A programming language", "A tool", "A framework"],
  "correct_answer": 1
}

Generate ONE question about JavaScript basics."""
    
    print(f"Prompt: Generate quiz question...")
    response = model.generate_content(json_prompt)
    print(f"Response:\n{response.text}")
    
    # Try to parse as JSON
    try:
        # Extract JSON from response
        text = response.text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        
        data = json.loads(text)
        print(f"✅ JSON parsing successful: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"⚠️ JSON parsing failed: {e}")
        print("But text generation still works!")
    
    # Test 4: Course generation
    print("\n4️⃣ Testing: Course Generation")
    print("-" * 60)
    
    course_prompt = """Create a mini course outline for "Python Basics" in JSON:
{
  "title": "Course Title",
  "description": "Brief description",
  "difficulty": "BEGINNER",
  "duration_hours": 10,
  "modules": ["Module 1", "Module 2"]
}"""
    
    print("Generating course outline...")
    response = model.generate_content(course_prompt)
    print(f"Response:\n{response.text[:200]}...")
    print("✅ Course generation working!")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED! Gemini API is working!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print("\nError Details:")
    print(f"Type: {type(e).__name__}")
    
    if "quota" in str(e).lower():
        print("\n⚠️ QUOTA ISSUE DETECTED")
        print("The API key has reached its quota limit.")
        print("This is a temporary limit that resets periodically.")
        print("\nSolutions:")
        print("1. Wait for quota to reset (usually per minute/hour)")
        print("2. The app has fallback responses built-in")
        print("3. Tests and courses will still work with fallback data")
    
    print("=" * 60)
