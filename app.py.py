from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import requests
import PyPDF2
import docx
import io
import re
import json
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from bs4 import BeautifulSoup
import hashlib
import uuid
import logging
from config import get_config

# Initialize Flask app
app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, origins=app.config['CORS_ORIGINS'])

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI API configuration
if app.config['OPENAI_API_KEY']:
    openai.api_key = app.config['OPENAI_API_KEY']

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summaries = db.relationship('Summary', backref='user', lazy=True, cascade='all, delete-orphan')

class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # video, blog, ebook, paragraph
    content_source = db.Column(db.Text, nullable=False)  # URL or file path or text
    original_content = db.Column(db.Text, nullable=True)
    summary_format = db.Column(db.String(20), nullable=False)  # bullets, paragraphs, notes, mindmap, keywords, slides
    summary_text = db.Column(db.Text, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)  # For caching
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    liked = db.Column(db.Boolean, default=False)

class ContentCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_hash = db.Column(db.String(64), unique=True, nullable=False)
    content_type = db.Column(db.String(20), nullable=False)
    extracted_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

# Content Extractors
class ContentExtractor:
    @staticmethod
    def extract_youtube_transcript(url):
        """Extract transcript from YouTube video"""
        try:
            # Extract video ID from URL
            video_id = None
            if "youtube.com/watch?v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            
            if not video_id:
                return None
            
            # Get transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([entry['text'] for entry in transcript])
            return text
        except Exception as e:
            print(f"Error extracting YouTube transcript: {e}")
            return None

    @staticmethod
    def extract_web_content(url):
        """Extract content from web pages/blogs"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content
            content_selectors = [
                'article', 'main', '.content', '.post-content',
                '.entry-content', '.article-body', '.post-body'
            ]
            
            content = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text()
                    break
            
            if not content:
                content = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:50000]  # Limit to 50k characters
        except Exception as e:
            print(f"Error extracting web content: {e}")
            return None

    @staticmethod
    def extract_pdf_content(file_path):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text[:50000]  # Limit to 50k characters
        except Exception as e:
            print(f"Error extracting PDF content: {e}")
            return None

    @staticmethod
    def extract_docx_content(file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text[:50000]  # Limit to 50k characters
        except Exception as e:
            print(f"Error extracting DOCX content: {e}")
            return None

# AI Summarizer
class AISummarizer:
    @staticmethod
    def create_prompt(content, format_type):
        """Create appropriate prompt based on format type"""
        prompts = {
            'bullets': f"""
Please summarize the following content into clear, concise bullet points. 
Focus on the main ideas and key takeaways. Use bullet points (•) format.

Content:
{content}

Summary in bullet points:
""",
            'paragraphs': f"""
Please summarize the following content into well-structured paragraphs. 
Create a coherent summary that flows naturally from one idea to the next.

Content:
{content}

Summary in paragraphs:
""",
            'notes': f"""
Please create short, concise notes from the following content. 
Focus on the most important points that someone would need to remember.

Content:
{content}

Short notes:
""",
            'mindmap': f"""
Please create a mind map structure from the following content.
Format it as a hierarchical structure with main topics and subtopics.

Content:
{content}

Mind map structure:
""",
            'keywords': f"""
Please extract the most important keywords and key phrases from the following content.
List them in order of importance.

Content:
{content}

Keywords:
""",
            'slides': f"""
Please create slide-style content from the following text.
Format it as if creating presentation slides with titles and bullet points.

Content:
{content}

Slide format:
"""
        }
        return prompts.get(format_type, prompts['bullets'])

    @staticmethod
    def generate_summary(content, format_type):
        """Generate summary using AI (mock implementation)"""
        # This is a mock implementation. In production, you would use:
        # - OpenAI API
        # - Anthropic Claude API
        # - Google Gemini API
        # - Local models like Llama, etc.
        
        try:
            # Mock AI response based on format
            mock_responses = {
                'bullets': """
• Main topic focuses on AI-powered content summarization technology
• Key benefits include time-saving and improved productivity
• Multiple input formats supported: videos, blogs, PDFs, and text
• Various output formats available: bullets, paragraphs, notes, mind maps
• Advanced AI algorithms ensure accurate and relevant summaries
• User-friendly interface designed for seamless experience
""",
                'paragraphs': """
This content discusses an innovative AI-powered summarization tool that transforms various types of content into digestible insights. The system supports multiple input formats including video URLs, blog articles, PDF documents, and raw text paragraphs.

The tool offers several output formats to suit different user preferences and use cases. Users can choose from bullet points for quick scanning, structured paragraphs for detailed understanding, concise notes for reference, mind maps for visual learning, keyword extraction for SEO purposes, and slide formats for presentations.

The underlying technology leverages advanced artificial intelligence algorithms to ensure accurate and contextually relevant summaries while maintaining the core message and important details of the original content.
""",
                'notes': """
- AI summarization tool for multiple content types
- Supports videos, blogs, PDFs, text input
- Output: bullets, paragraphs, notes, mind maps, keywords, slides
- Time-saving and productivity-focused
- Advanced AI ensures accuracy
- User-friendly design
""",
                'mindmap': """
AI Summarization Tool
├── Input Types
│   ├── Video URLs (YouTube, Vimeo)
│   ├── Blog Articles & Web Content
│   ├── PDF Documents
│   └── Text Paragraphs
├── Output Formats
│   ├── Bullet Points
│   ├── Structured Paragraphs
│   ├── Short Notes
│   ├── Mind Maps
│   ├── Keywords
│   └── Presentation Slides
└── Benefits
    ├── Time-saving
    ├── Improved Productivity
    ├── Multiple Formats
    └── AI-powered Accuracy
""",
                'keywords': """
AI summarization, content processing, video transcription, blog summarization, PDF extraction, text analysis, bullet points, mind mapping, keyword extraction, productivity tool, artificial intelligence, content optimization, document processing, web scraping, YouTube transcripts
""",
                'slides': """
Slide 1: AI-Powered Summarization
• Transform any content into digestible insights
• Save time and boost productivity

Slide 2: Supported Input Types
• Video URLs (YouTube, Vimeo, etc.)
• Blog articles and web content
• PDF documents and eBooks
• Raw text and paragraphs

Slide 3: Output Formats
• Bullet points for quick scanning
• Structured paragraphs for detail
• Concise notes for reference
• Visual mind maps
• SEO keywords
• Presentation slides

Slide 4: Key Benefits
• Advanced AI algorithms
• Multiple format support
• User-friendly interface
• Accurate summarization
"""
            }
            
            return mock_responses.get(format_type, mock_responses['bullets'])
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Sorry, there was an error generating the summary. Please try again."

# Utility Functions
def generate_content_hash(content):
    """Generate hash for content caching"""
    return hashlib.sha256(content.encode()).hexdigest()

def get_session_id():
    """Generate or get session ID"""
    return str(uuid.uuid4())

# Routes
@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('.', 'index.html')

@app.route('/api/summarize', methods=['POST'])
@limiter.limit("10 per minute")
def summarize_content():
    """Main summarization endpoint"""
    try:
        data = request.get_json()
        
        content_type = data.get('content_type')  # video, blog, ebook, paragraph
        content_source = data.get('content_source')  # URL or text
        summary_format = data.get('format', 'bullets')
        session_id = data.get('session_id', get_session_id())
        
        if not content_type or not content_source:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Extract content based on type
        extracted_content = None
        
        if content_type == 'video':
            if 'youtube.com' in content_source or 'youtu.be' in content_source:
                extracted_content = ContentExtractor.extract_youtube_transcript(content_source)
                if not extracted_content:
                    return jsonify({'error': 'Could not extract transcript. Video may not have captions or may be private.'}), 400
            else:
                return jsonify({'error': 'Only YouTube videos are supported currently'}), 400
                
        elif content_type == 'blog':
            extracted_content = ContentExtractor.extract_web_content(content_source)
            if not extracted_content:
                return jsonify({'error': 'Could not extract content from URL. Please check if the URL is accessible.'}), 400
            
        elif content_type == 'paragraph':
            extracted_content = content_source
            if len(extracted_content.strip()) < 50:
                return jsonify({'error': 'Text is too short. Please provide at least 50 characters.'}), 400
            
        elif content_type == 'ebook':
            # For ebook, content_source should be the extracted content from upload
            extracted_content = content_source
            
        else:
            return jsonify({'error': 'Unsupported content type'}), 400
        
        if not extracted_content or len(extracted_content.strip()) < 10:
            return jsonify({'error': 'Could not extract sufficient content from source'}), 400
        
        # Limit content length
        if len(extracted_content) > app.config['MAX_CONTENT_CHARS']:
            extracted_content = extracted_content[:app.config['MAX_CONTENT_CHARS']]
            logger.info(f"Content truncated to {app.config['MAX_CONTENT_CHARS']} characters")
        
        # Check cache first
        content_hash = generate_content_hash(extracted_content + summary_format)
        cached_summary = Summary.query.filter_by(
            content_hash=content_hash,
            summary_format=summary_format
        ).first()
        
        if cached_summary:
            return jsonify({
                'success': True,
                'summary': cached_summary.summary_text,
                'session_id': session_id,
                'cached': True
            })
        
        # Generate new summary
        summary_text = AISummarizer.generate_summary(extracted_content, summary_format)
        
        # Save to database
        summary = Summary(
            session_id=session_id,
            content_type=content_type,
            content_source=content_source,
            original_content=extracted_content[:10000],  # Store first 10k chars
            summary_format=summary_format,
            summary_text=summary_text,
            content_hash=content_hash
        )
        
        db.session.add(summary)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'summary': summary_text,
            'session_id': session_id,
            'summary_id': summary.id,
            'cached': False
        })
        
    except Exception as e:
        print(f"Error in summarize_content: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for ebooks/PDFs"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extract content based on file type
            extracted_content = None
            if filename.lower().endswith('.pdf'):
                extracted_content = ContentExtractor.extract_pdf_content(file_path)
            elif filename.lower().endswith('.docx'):
                extracted_content = ContentExtractor.extract_docx_content(file_path)
            else:
                os.remove(file_path)  # Clean up
                return jsonify({'error': 'Unsupported file type'}), 400
            
            # Clean up file
            os.remove(file_path)
            
            if not extracted_content:
                return jsonify({'error': 'Could not extract content from file'}), 400
            
            return jsonify({
                'success': True,
                'content': extracted_content[:1000] + '...' if len(extracted_content) > 1000 else extracted_content,
                'full_content': extracted_content
            })
            
    except Exception as e:
        print(f"Error in upload_file: {e}")
        return jsonify({'error': 'File upload failed'}), 500

@app.route('/api/summary/<int:summary_id>/like', methods=['POST'])
def like_summary(summary_id):
    """Like/unlike a summary"""
    try:
        summary = Summary.query.get_or_404(summary_id)
        summary.liked = not summary.liked
        db.session.commit()
        
        return jsonify({
            'success': True,
            'liked': summary.liked
        })
        
    except Exception as e:
        print(f"Error in like_summary: {e}")
        return jsonify({'error': 'Failed to update like status'}), 500

@app.route('/api/summaries/<session_id>', methods=['GET'])
def get_session_summaries(session_id):
    """Get all summaries for a session"""
    try:
        summaries = Summary.query.filter_by(session_id=session_id).order_by(Summary.created_at.desc()).all()
        
        result = []
        for summary in summaries:
            result.append({
                'id': summary.id,
                'content_type': summary.content_type,
                'content_source': summary.content_source[:100] + '...' if len(summary.content_source) > 100 else summary.content_source,
                'summary_format': summary.summary_format,
                'summary_text': summary.summary_text,
                'liked': summary.liked,
                'created_at': summary.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'summaries': result
        })
        
    except Exception as e:
        print(f"Error in get_session_summaries: {e}")
        return jsonify({'error': 'Failed to retrieve summaries'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Database initialization
def create_tables():
    """Create database tables"""
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        create_tables()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = app.config['ENV'] == 'development'
    
    logger.info(f"Starting Quicky AI Summarizer on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Environment: {app.config['ENV']}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
