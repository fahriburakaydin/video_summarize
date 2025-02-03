
import re
import yt_dlp
import openai 
import whisper
import os
from youtube_transcript_api import YouTubeTranscriptApi


def get_video_id(url): 
    """Extracts the video ID from a YouTube URL."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_url, language="en"):
    """Fetches the transcript of a YouTube video if available."""
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        text = " ".join([entry['text'] for entry in transcript])
        return text
    except Exception:
        return None  # No transcript available
    
def download_audio(video_url):
    """Downloads the audio from a YouTube video without ffmpeg by selecting a specific format."""
    ydl_opts = {
        'format': '140',  # Uses m4a audio format (no ffmpeg needed)
        'outtmpl': 'video_audio.m4a',  # Fixed filename with m4a extension
        'cookies_from_browser': ('chrome',),
        'quiet': True,  # Reduce output noise
        'ignoreerrors': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def transcribe_audio():
    """Transcribes the downloaded audio using Whisper."""
    model = whisper.load_model("small")  # Ensure Whisper can read .m4a files
    result = model.transcribe("video_audio.m4a")
    return result["text"]


def summarize_text(text):
    """Summarizes the text using OpenAI's GPT model and returns token usage."""
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Summarize the following transcript in a concise way."},
            {"role": "user", "content": text}
        ]
    )   
    summary = response["choices"][0]["message"]["content"].strip()
    tokens_used = response["usage"]["total_tokens"]
    return summary, tokens_used


if __name__ == "__main__":
    video_url = input("Enter YouTube video URL: ")
    try:
        transcript = get_transcript(video_url)
        if not transcript:
            print("No subtitles available, transcribing audio...")
            download_audio(video_url)
            transcript = transcribe_audio()
        
        summary, tokens_used = summarize_text(transcript)
        print("\nSummary:\n", summary)
        print(f"\nTokens used: {tokens_used}")
    except Exception as e:
        print("Error:", e)
