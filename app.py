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

load_dotenv()

#set up openai api key
my_api_key = os.getenv('OPENAI_API_KEY')
test_mode = os.getenv('TEST_MODE')
client = OpenAI(api_key=my_api_key)

#setup flask secret key as a random string
app = Flask(__name__)
app.secret_key = os.urandom(24)


def extract_video_id(url):
    """Extracts the YouTube video ID from a URL."""
    query = urlparse(url).query  # Extract query string (e.g., "v=dQw4w9WgXcQ")
    video_id = parse_qs(query).get('v')  # Get the value of 'v'
    if video_id:
        return video_id[0]  # Return the first match
    return None


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
    """Summarizes text using OpenAI's GPT-4o-mini model."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": 
                   """You are a helpful assistant that summarizes text. 
                   You will be given a transcript of a youtube video and you will need to summarize it in a few sentences.
                   Make sure to keep the most important information and remove any unnecessary details.
                   Use bullet points to list the important highlights
                   if it is multiple speakers, try to guess what is happening in the video, but don't make up anything.
                   Ensure that you make it clear when you are guessing what is happening in the video"""}, 
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
    
def generate_answer(question, transcript):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Answer the user's question based on this transcript:\n\n{transcript[:3000]}"},  # Trim to avoid token limits
                {"role": "user", "content": question}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {str(e)}"
    


#this is the route for the home page
@app.route('/') 
def home():
    return render_template('index.html')  # Shows the form

#this is the route for the summarize page
@app.route('/summarize', methods=['POST']) 
def summarize():

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
        return "Invalid YouTube URL. Please try again."

    print("\n===== DEBUG START =====")  # Debug marker
    print(f"Video ID: {video_id}")

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
            return "Failed to download audio. Please try another video."

        #transcribe audio
        print("\n[3] Attempting transcription...")
        text = transcribe_audio(audio_path)
        if not text:
            print("[3] Transcription failed!")
            return "Failed to transcribe audio. Please try another video."
        
    #summarize text regardles of the source
    print("\n[4] Attempting summarization...")
    result = summarize_text(text)  # Returns a dictionary
    summary = result["summary"]    # Extract summary
    tokens_used = result["tokens_used"]
    if not summary:
        print("[4] Summarization failed!")
        return "Failed to summarize text. Please try another video."

    session['transcript'] = text
    session['summary'] = summary
    print(text)
    print(summary)
    print(tokens_used) 
    print(session['transcript'])
    print(session['summary'])
    print("\n===== DEBUG END =====")
    
    return render_template('summary.html', summary=summary, tokens_used=tokens_used)   ###, tokens_used=tokens_used)

#this is the route for the ask page
@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    transcript = session.get('transcript', '')  # Retrieve stored transcript

    if not transcript:
        return "Error: No transcript found. Start over."

    # Generate answer using OpenAI
    answer = generate_answer(question, transcript)
    return render_template("summary.html", summary=session.get('summary'), answer=answer, transcript=session.get('transcript')[:1000])

if __name__ == '__main__':
    print(f"test_mode: {test_mode}")
    app.run(debug=True)