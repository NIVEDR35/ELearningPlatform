# Adaptive Learning System - Setup Instructions

## Overview
This is an AI-powered Adaptive Learning Management System built with Flask (Python). It features:
- VARK Learning Style Detection
- AI-Generated Courses (using Google Gemini)
- YouTube Video Integration
- Real-time Progress Tracking
- Hybrid Recommendation System
- Timed Quizzes with Feedback

---

## Prerequisites

### Required Software
1. **Python 3.9 or higher**
   - Download from: https://www.python.org/downloads/
   - **IMPORTANT**: During installation, check "Add Python to PATH"

### Required API Keys
You'll need these API keys (both are free):

1. **Google Gemini API Key** (for AI content generation)
   - Go to: https://makersuite.google.com/app/apikey
   - Sign in with Google account
   - Click "Create API Key"
   - Copy the key

2. **YouTube Data API Key** (for video search)
   - Go to: https://console.cloud.google.com/
   - Create a new project (or use existing)
   - Enable "YouTube Data API v3"
   - Go to Credentials > Create Credentials > API Key
   - Copy the key

---

## Quick Start (Windows)

### Step 1: Extract the ZIP
Extract the ZIP file to a folder (e.g., `C:\AdaptiveLearning`)

### Step 2: Run Setup
1. Double-click `setup.bat`
2. Wait for the setup to complete
3. This will create a virtual environment and install dependencies

### Step 3: Configure API Keys
1. Open the `.env` file in a text editor (Notepad)
2. Replace the placeholder values:
   ```
   GEMINI_API_KEY=your_actual_gemini_key_here
   YOUTUBE_API_KEY=your_actual_youtube_key_here
   ```
3. Save and close the file

### Step 4: Run the Application
1. Double-click `run.bat`
2. Wait for the server to start
3. Open your browser and go to: **http://localhost:5002**

### Step 5: Stop the Server
- Press `Ctrl+C` in the command window, OR
- Double-click `stop.bat`

---

## Manual Setup (Alternative)

If the batch files don't work, follow these steps in Command Prompt:

```cmd
# Navigate to the project folder
cd C:\path\to\AdaptiveLearningSystem

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file and add your API keys (see above)

# Run the application
set PORT=5002
python app.py
```

---

## Default Login

The system creates a default user on first run:
- **Email**: test@example.com
- **Password**: password123

Or you can register a new account.

---

## Features Guide

### 1. Dashboard
- View your learning progress
- See personalized recommendations
- Track daily goals and streaks

### 2. Courses
- Browse AI-generated courses
- Watch YouTube videos with embedded quizzes
- Track completion progress

### 3. Tests
- Take timed skill assessments (5 minutes)
- Get instant feedback with correct/wrong answers
- View detailed explanations

### 4. Recommendations
- Get personalized course suggestions
- Based on your VARK learning style
- Adapts to your progress

---

## Troubleshooting

### "Python not found" Error
- Make sure Python is installed
- Reinstall Python and check "Add Python to PATH"

### "Module not found" Error
- Run `setup.bat` again
- Or manually: `pip install -r requirements.txt`

### "API Key Error" or No AI Content
- Check your `.env` file has valid API keys
- Make sure there are no spaces around the `=` sign

### Port Already in Use
- Edit `.env` and change `PORT=5002` to another port (e.g., `PORT=5003`)
- Or close other applications using that port

### Database Errors
- Delete the `adaptive_learning.db` file
- Restart the application (it will create a fresh database)

---

## Project Structure

```
AdaptiveLearningSystem/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (API keys)
├── setup.bat             # Windows setup script
├── run.bat               # Windows run script
├── stop.bat              # Windows stop script
├── templates/            # HTML templates
│   ├── dashboard.html
│   ├── course_detail.html
│   ├── tests.html
│   └── ...
├── static/               # Static files (CSS, JS)
└── services/
    ├── gemini_service.py
    ├── youtube_service.py
    ├── vark_service.py
    └── ...
```

---

## Contact

If you have any issues, please contact the developer.

Happy Learning! 🎓
