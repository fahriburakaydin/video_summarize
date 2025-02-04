from flask import Flask, render_template, request, session
from urllib.parse import urlparse, parse_qs  # For URL parsing
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import os
import openai
import yt_dlp
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import traceback


load_dotenv()

#set up openai api key
my_api_key = os.getenv('OPENAI_API_KEY')
test_mode = os.getenv('TEST_MODE')
client = OpenAI(api_key=my_api_key)

#setup flask secret key as a random string
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Limit by IP
    default_limits=["5 per minute"]  # Adjust as needed
)


def extract_video_id(url):
    """Extracts the YouTube video ID from a URL."""
    query = urlparse(url).query  # Extract query string (e.g., "v=dQw4w9WgXcQ")
    video_id = parse_qs(query).get('v')  # Get the value of 'v'
    if video_id:
        return video_id[0]  # Return the first match
    return None

def get_video_details(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        video_length = info.get('duration', 0)  # Length in seconds
        upload_date = info.get('upload_date', 'Unknown Date')  # YYYYMMDD format

        # Convert upload_date to YYYY-MM-DD
        if upload_date != 'Unknown Date':
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        return video_title, video_length, upload_date


def download_audio(video_id):
    """Downloads the audio of a YouTube video using yt-dlp."""
    try:
        # Ensure "audio" folder exists if not create it
        os.makedirs("audio", exist_ok=True)

        # yt-dlp options
        ydl_opts = {
            'format': '140',  # m4a format (no ffmpeg needed)
            'outtmpl': f'audio/{video_id}.mp3',  # Save to audio folder
            'quiet': True,  # Suppress output
            'ignoreerrors': True,  # Skip errors
            'cookies_from_browser': ('chrome',),  # Use browser cookies
        }

        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com/watch?v={video_id}"])

        # Check if file was downloaded
        audio_path = f"audio/{video_id}.mp3"
        if os.path.exists(audio_path):
            print(f"[2] Audio downloaded: {audio_path}")
            return audio_path
        else:
            print("[2] Audio download failed!")
            return None

    except Exception as e:
        print(f"[2] Audio download error: {str(e)}")
        return None
   


def transcribe_audio(audio_path):
    """Transcribes audio using OpenAI's Whisper model."""
    try:
        with open(f"{Path.cwd()}/{audio_path}", "rb") as audio_file:
            transcript =client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
                )
        return transcript.text
    except Exception as e:
        print(f"[3] Transcription error: {str(e)}")
        return None
    

def summarize_text(text):
    try:
        """Summarizes text using OpenAI's GPT-4o-mini model."""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": 
                    """You are a YouTube video summarizer. Follow these rules:
                            1. Start with a 1-sentence overview.
                            2. List 3-5 key points as bullet points.
                            3. Highlight technical terms or tools mentioned, if significant.
                            4. If multiple speakers, note their roles.
                            5. Avoid speculation; only use transcript content."""}, 

                    {"role": "user", "content": f"""Here is the transcript of the video you will summarize: {text}. 
                    Keep your summary concise and to the point. Make sure you clearly state what is covered in the video.
                    Use bullet points to list the important highlights"""}
                    ],
                    temperature=0.3,
            max_tokens=150
        )
        return {
                "summary": response.choices[0].message.content,  # Summary text
                "tokens_used": response.usage.total_tokens       # Tokens used
            }
    except openai.OpenAIError as e:  # Catch OpenAI API errors
        print(f"[ERROR] OpenAI API failure: {str(e)}")
        return {"summary": "Error: AI summarization failed. Try again later.", "tokens_used": 0}
    except Exception as e:
        print(f"[ERROR] Unexpected failure in summarization: {str(e)}")
        return {"summary": "An unexpected error occurred.", "tokens_used": 0}
    
def generate_answer(question, transcript):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f""" 
                 Answer the user's question using this transcript.
                Rules:
                1. If the answer isn't in the transcript, say "I don't know."
                2. Be concise (1-2 sentences).
                3. Format technical terms in **bold**.
                Transcript:\n{transcript[:3000]}"""},  # Trim to avoid token limits
                
                {"role": "user", "content": question}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {str(e)}"
    


#handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_message="Page not found."), 404

# Handle 500 errors (server errors)
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message="Internal server error. Please try again later."), 500


#this is the route for the home page
@app.route('/') 
def home():
    return render_template('index.html')  # Shows the form

#this is the route for the summarize page
@app.route('/summarize', methods=['POST']) 
@limiter.limit("3 per minute") # Limit requests to 3 per minute
def summarize():
    try:
        # Check if testing mode is enabled in the environment variable
        if os.environ.get('TEST_MODE') == 'true':
            # Use static data
            static_transcript = """This is statictranscript: Tabii ki. Sağ olun. Türkiye gördük sizi maşallah diyelim. Sizi gördüyseniz iyiyiz. Eee neler söyleyeceksiniz? Sağlık durumunuz nedir? Uzun bir süre hastanede kaldınız. Her şeye geri döneceğim. Merak etmeyin. Hem de fazlasıyla geri döneceğimiz. Ben olmadığı kadar daha iyi. Sağlık hayatı çok önemli bir şey. Herkese sağlık diliyorum. Eee sağlığınızda çok dikkat edin. Her şey benim derken bir anda hiçbir şeyiniz kalmayabiliyor hayatta. Ben de onu yaşadım. Son kırk gün içerisinde. Her şeyim var derken bir şeyim kalmadı bir anda. Etrafımdaki herkes elimdeki her şeyi aldı. Bunlar çocuklarım da dahil. Çocuğum da dahil. Ama şükür hala sevenlerim var. Onlarla yaşayacağım. Tanrı'yla, Allah'la yaşayacağım. Sağ olun. Teşekkür ederim. Abi geri döneceğim dediniz. Neleri kastettiniz? Her şeyi kastettim. Hem yazı, hesap hem bir serimizden kuruyorum. Her şeyi kastettim. Her şeyle geri döneceğim. Eminim. Çocuklarınızla ilgili de eee birçok haberler okudunuz. Onlarla da onlarla da geri döneceğim. Onlar ok..."""
            static_summary = "'- The speaker expresses gratitude and acknowledges their audience.\n- They discuss their recent health struggles, having spent a long time in the hospital.\n- Emphasizes the importance of health and wishes everyone well.\n- Reflects on a personal experience of losing everything suddenly, including relationships with their children.\n- Despite challenges, they express hope and determination to return to their previous life, including writing and reconnecting with family.\n- Mentions plans to come back stronger and engage with their children again.',"
            tokens_used = 0  # Simulate no token usage
            
            session['transcript'] = static_transcript
            session['summary'] = static_summary
            return render_template('summary.html', summary=static_summary, tokens_used=tokens_used)

        url = request.form['youtube_url']
        video_id = extract_video_id(url)
        if not video_id:
            return render_template('error.html', error_message="Invalid YouTube URL. Please check and try again."), 400

        print("\n===== DEBUG START =====")  # Debug marker
        print(f"Video ID: {video_id}")
        
        # Get video details
        video_title, video_length, upload_date = get_video_details(url)
        print(f"Title: {video_title}, Length: {video_length} sec, Upload Date: {upload_date}")

        
        
        # Try subtitles first
        try:
            print("\n[1] Trying to fetch subtitles...")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([line['text'] for line in transcript])
            print("[1] Success! Subtitles found.")
        except Exception as e:
            print(f"[1] Subtitle fetch failed: {str(e)}")

            # Fallback to audio
            print("\n[2] Attempting audio download...")
            audio_path = download_audio(video_id)
            if not audio_path:
                print("[2] Audio download failed!")
                return render_template('error.html', error_message="Failed to download audio. Please try another video."), 400

            #transcribe audio
            print("\n[3] Attempting transcription...")
            text = transcribe_audio(audio_path)
            if not text:
                print("[3] Transcription failed!")
                return render_template('error.html', error_message="Failed to transcribe audio. Please try another video."), 400
            
        #summarize text regardles of the source
        print("\n[4] Attempting summarization...")
        result = summarize_text(text)  # Returns a dictionary
        summary = result["summary"]    # Extract summary
        tokens_used = result["tokens_used"]
        if not summary:
            print("[4] Summarization failed!")
            return render_template('error.html', error_message="Failed to summarize text. Please try another video."), 400
        
        session['transcript'] = text
        session['summary'] = summary
        session['video_id'] = video_id
        session['video_title'] = video_title
        session['video_length'] = video_length
        session['upload_date'] = upload_date

    #   print(text)
    #   print(summary)
    #   print(tokens_used) 
    #   print(session['transcript'])
    #   print(session['summary'])
    #   print("\n===== DEBUG END =====")
        
        return render_template(
            'summary.html',
            summary=summary,
            tokens_used=tokens_used,
            video_id=video_id,
            video_title=video_title,
            video_length=video_length,
            upload_date=upload_date
        )
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[ERROR] {error_details}")  # Log full traceback
    return render_template('error.html', error_message="An unexpected error occurred. Please try again."), 500
    
#this is the route for the ask page
@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    transcript = session.get('transcript', '')  # Retrieve stored transcript

    if not transcript:
        return "Error: No transcript found. Start over."

    # Generate answer using OpenAI
    answer = generate_answer(question, transcript)
    return render_template("summary.html", summary=session.get('summary'), answer=answer, transcript=session.get('transcript')[:1000], video_id=session.get('video_id'), video_title=session.get('video_title'), video_length=session.get('video_length'), upload_date=session.get('upload_date'))

if __name__ == '__main__':
    print(f"test_mode: {test_mode}")
    app.run(debug=True)