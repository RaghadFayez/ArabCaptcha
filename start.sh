#!/bin/bash
echo "Starting ArabCaptcha Startup Script..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Seed the database
echo "Seeding the database..."
python seed.py

# Start the uvicorn server
echo "Starting the backend server..."
uvicorn app.main:app --reload
