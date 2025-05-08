# Video Summarize

A Flask web application and command-line tool to fetch, transcribe, and summarize YouTube videos using large language models (OpenAI or Google).

## Features

* **YouTube Integration**: Extracts video ID and metadata (title, duration, upload date).
* **Transcript Retrieval**: Attempts `YouTubeTranscriptApi` and falls back to downloading audio via `yt_dlp` if necessary.
* **Audio Transcription**: Uses Whisper (OpenAI) or Google Speech-to-Text to transcribe audio files.
* **Summarization**: Generates a one-sentence overview and 3–5 bullet points, highlights technical details, and identifies speaker roles using chat-based LLMs.
* **Q\&A Interface**: Ask follow-up questions about the transcript on the web UI.
* **Rate Limiting**: Caps `/summarize` to 3 requests/min per IP and 5 requests/min globally via `flask_limiter`.
* **Configurable LLM Providers**: Easily switch between OpenAI and Google Generative AI.

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/fahriburakaydin/video_summarize.git
   cd video_summarize
   ```
2. **Set up a virtual environment and install dependencies**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** at the project root. See **Configuration** below.

## Configuration

Configure required environment variables in `.env`:

```dotenv
SECRET_KEY=your_flask_secret_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key       # Required if using Google provider
YOUTUBE_COOKIES=path/to/youtube_cookies.txt  # Optional, for age-restricted or private videos
LLM_PROVIDER=openai                       # Options: 'openai' or 'google'
LLM_MODEL=gpt-4                           # Or another compatible model
```

## Usage

### Web Application

1. **Start the Flask server**:

   ```bash
   flask run
   ```
2. **Open** `http://localhost:5000` in your browser.
3. **Paste** a YouTube video URL and click **Summarize**.
4. **View** the summary and ask follow-up questions on the same page.

### Command-Line Interface

Run the standalone CLI script:

```bash
python video_sum.py <YouTube_URL>
```

This will print the transcript and summary directly to your console.

## Rate Limiting

* **Per-IP**: 3 `/summarize` requests per minute.
* **Global**: 5 `/summarize` requests per minute.

These limits are enforced by `flask_limiter` in `app.py`.

## LLM Providers

* **OpenAIProvider**: Uses OpenAI Chat API for summarization/Q\&A and Whisper for transcription.
* **GoogleProvider**: Uses Google Generative AI client for both text generation and audio transcription.

Switch providers by setting `LLM_PROVIDER` in your `.env` file.

## Project Structure

```
video_summarize/
├── app.py             # Flask application
├── llm_providers.py   # Abstract LLM layer and factory
├── video_sum.py       # CLI entry point
├── templates/         # HTML templates
│   ├── index.html
│   ├── summary.html
│   └── error.html
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
