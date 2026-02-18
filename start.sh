#!/bin/bash

# Adaptive Learning System - Startup Script

echo "======================================================================"
echo "  🧠 Adaptive Learning System - AI-Powered Personalized Learning"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
if [ ! -f ".dependencies_installed" ]; then
    echo -e "${YELLOW}📥 Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    touch .dependencies_installed
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚙️  Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your GEMINI_API_KEY${NC}"
    echo ""
fi

# Initialize database if needed
if [ ! -f "adaptive_learning.db" ]; then
    echo -e "${YELLOW}🗄️  Initializing database...${NC}"
    python init_db.py --seed
    echo -e "${GREEN}✅ Database initialized with sample data${NC}"
else
    echo -e "${GREEN}✅ Database already exists${NC}"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}🚀 Starting Adaptive Learning Platform...${NC}"
echo "======================================================================"
echo ""
echo -e "${BLUE}📍 Server will be available at: http://localhost:5001${NC}"
echo ""
echo -e "${YELLOW}Sample Users:${NC}"
echo "  - alice@example.com (password: password123) - Visual learner"
echo "  - bob@example.com (password: password123) - Kinesthetic learner"
echo "  - charlie@example.com (password: password123) - New user"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo "======================================================================"
echo ""

# Run the application
python app.py
