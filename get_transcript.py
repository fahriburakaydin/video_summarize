from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import whisper
import re

def get_video_id(url): 
    """Extracts the video ID from a YouTube URL."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_url):
    """Fetches the transcript of a YouTube video if available."""
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])
        return text
    except Exception as e:
        return f"Error: {e}"

    

def download_audio(video_url):
    # Extract video ID
    video_id = video_url.split("v=")[-1].split("&")[0]
    
    # Set up yt-dlp options to download audio
    options = {
        'format': 'bestaudio/best',  # Download best audio quality
        'extractaudio': True,        # Extract audio
        'audioquality': 0,           # Best audio quality
        'outtmpl': 'downloads/%(id)s.%(ext)s',  # Save in a folder
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        audio_file = f"downloads/{info_dict['id']}.m4a"  # The audio file path
    return audio_file

def transcribe_audio(audio_file):
    # Load the whisper model
    model = whisper.load_model("base")

    # Transcribe the audio
    result = model.transcribe(audio_file)
    return result['text']



# Example usage
if __name__ == "__main__":
    video_link = input("Enter a YouTube video URL: ")
    video_id = get_video_id(video_link)
    transcript = get_transcript(video_id)
    
    # Check if transcript is too short or the video has no transcript
    if len(transcript) < 100:
        print("This video might not have subtitles or the API couldn't fetch them.")
    else:
        print("\nFull Transcript:\n", transcript)
