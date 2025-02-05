from flask import Flask, render_template, request, session
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import os
import yt_dlp
from pathlib import Path
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import traceback
from llm_providers import LLMProviderFactory


load_dotenv()

# Initialize Flask app and LLM provider
app = Flask(__name__)
app.secret_key = os.urandom(24)
llm_provider = LLMProviderFactory.get_provider()

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5 per minute"]
)

def extract_video_id(url):
    """Extracts the YouTube video ID from a URL."""
    query = urlparse(url).query
    video_id = parse_qs(query).get('v')
    return video_id[0] if video_id else None

def get_video_details(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        video_length = info.get('duration', 0)
        upload_date = info.get('upload_date', 'Unknown Date')

        # Convert upload_date to YYYY-MM-DD
        if upload_date != 'Unknown Date':
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        return video_title, video_length, upload_date

def download_audio(video_id):
    """Downloads the audio of a YouTube video using yt-dlp."""
    try:
        # Ensure "audio" folder exists
        os.makedirs("audio", exist_ok=True)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'audio/{video_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com/watch?v={video_id}"])

        audio_path = f"audio/{video_id}.mp3"
        return audio_path if os.path.exists(audio_path) else None
    except Exception as e:
        print(f"Audio download error: {str(e)}")
        return None

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
@limiter.limit("3 per minute")
def summarize():
    try:
        # Check if testing mode is enabled
        if os.environ.get('TEST_MODE') == 'true':
            # Use static data for testing
            return render_template('summary.html', 
                                   summary="Test summary", 
                                   tokens_used=0)

        url = request.form['youtube_url']
        video_id = extract_video_id(url)
        if not video_id:
            return render_template('error.html', error_message="Invalid YouTube URL"), 400

        # Get video details
        video_title, video_length, upload_date = get_video_details(url)

        # Try to get subtitles first
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([line['text'] for line in transcript])
        except Exception:
            # Fallback to audio download and transcription
            audio_path = download_audio(video_id)
            if not audio_path:
                return render_template('error.html', error_message="Failed to download audio"), 400

            text = llm_provider.transcribe_audio(audio_path)
            if not text:
                return render_template('error.html', error_message="Failed to transcribe audio"), 400

        # Summarize text
        summary = llm_provider.summarize_text(text)
        print(summary)
        if not summary or summary.startswith("Error in summarization"):
            return render_template('error.html', error_message="Failed to generate summary"), 400


        # Store in session for potential follow-up questions
        
        session['transcript'] = text
        session['video_id'] = video_id
        session['video_title'] = video_title
        session['video_length'] = video_length
        session['upload_date'] = upload_date

        print(f"llm: {llm_provider}")
        

        return render_template(
            'summary.html',
            summary=summary,
            video_id=video_id,
            video_title=video_title,
            video_length=video_length,
            upload_date=upload_date
        )
    except Exception as e:
        traceback.print_exc()
        return render_template('error.html', error_message="An unexpected error occurred"), 500

@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    transcript = session.get('transcript', '')

    if not transcript:
        return render_template('error.html', error_message="No transcript found. Please start over.")

    # Generate answer
    answer = llm_provider.generate_answer(question, transcript)

    return render_template(
        "summary.html", 
        summary=session.get('summary'),
        answer=answer, 
        video_id=session.get('video_id'),
        video_title=session.get('video_title'),
        video_length=session.get('video_length'),
        upload_date=session.get('upload_date')
    )

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_message="Page not found."), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message="Internal server error."), 500

if __name__ == '__main__':
    app.run(debug=True)