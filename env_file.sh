# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///quicky.db

# AI API Keys (choose one or multiple)
OPENAI_API_KEY=fWXiz5MNdpFQ5mRpjzSL6HCjSe-Y7MxNxizkAV8lrO5ExbBbeiYoYaPLKkxOajxIHN5Pa1tPPeT3BlbkFJOhyHyTn9Ab1Q5xgXJMsKBHJIlgX0bcJtOivXwFrO1mR-0o96unrGQXEjLr0GlYT4MoEny8H2cA
ANTHROPIC_API_KEY=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
GOOGLE_API_KEY=AIzaSyA_lgb_-Yo2fR__j6N91l_gQK0T97Et14I

# File Upload Settings
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads

# CORS Settings
CORS_ORIGINS=*

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
