# Google Audio Podcast Generator

A powerful Python application that generates realistic podcast-style conversations using Google's Gemini 2.5 Pro Preview TTS (Text-to-Speech) model. Create multi-speaker audio content with distinct voices for engaging podcast episodes.

## Features

- **Multi-Speaker TTS**: Generate conversations with multiple distinct voices (Zephyr, Puck)
- **Dual Interface**: Both a Command-Line Interface (CLI) and a REST API server.
- **YouTube Conversion**: Generate a podcast directly from a YouTube video URL.
- **Audio Format Support**: Outputs MP3 format with proper audio headers.
- **Streaming Audio**: Real-time audio generation and streaming responses from the API.
- **Voice Configuration**: Configurable speaker voices for realistic conversations.
- **CORS Support**: Web-friendly API with cross-origin resource sharing.

## Prerequisites

- Python 3.7 or higher
- Google Gemini API key (get yours at [Google AI Studio](https://makersuite.google.com/app/apikey))
- FFmpeg: Required for audio conversion. Install it using your system's package manager (e.g., `sudo apt-get install ffmpeg` on Debian/Ubuntu, `brew install ffmpeg` on macOS).

## Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd GoogleAudioPodcast
    ```

2.  **Create and activate virtual environment**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On macOS/Linux
    # .venv\Scripts\activate   # On Windows
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Set up environment variables**
    Create a `.env` file in the project root and add your Gemini API key:
    ```bash
    echo "GEMINI_API_KEY=your_actual_api_key_here" > .env
    ```

## Usage

This project offers two primary ways to generate podcasts: a Command-Line Interface (CLI) for local generation and a FastAPI server for web-based interaction.

### Command-Line Interface (CLI)

The `cli.py` script provides a user-friendly way to generate podcasts from your terminal.

**1. Generate from Text**

Create a podcast from a string of text or a text file.

```bash
# Generate from a simple text string
python cli.py generate-text "Speaker 1: Hello world. Speaker 2: Hi there."

# Generate from a text file
python cli.py generate-text /path/to/your/script.txt

# Specify an output file
python cli.py generate-text "My text" -o my_podcast.mp3
```

**2. Generate from a YouTube URL**

Transcribe a YouTube video and generate a podcast from its content.

```bash
# Generate from a YouTube URL
python cli.py generate-youtube "https://www.youtube.com/watch?v=your_video_id"

# Specify an output file
python cli.py generate-youtube "https://www.youtube.com/watch?v=your_video_id" -o youtube_podcast.mp3
```

### REST API Server

Start the API server for HTTP-based podcast generation.

```bash
# Start the API server
python -m uvicorn src.api:app --reload
# Server available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## API Documentation

### POST /generate-podcast

Generate a podcast audio file from text input.

**Request Body:**
```json
{
  "text": "Speaker 1: Welcome to our podcast! Speaker 2: Thanks for having me! Speaker 1: Let's dive into today's topic."
}
```

**Response:** Streaming MP3 audio file

**Example Usage:**
```bash
# Using curl
curl -X POST "http://localhost:8000/generate-podcast" \
     -H "Content-Type: application/json" \
     -d '{"text": "Speaker 1: Hello! Speaker 2: Hi there!"}' \
     --output podcast.mp3
```

### POST /convert-youtube

Generate a podcast audio file from a YouTube video URL.

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=your_video_id"
}
```

**Response:** Streaming MP3 audio file

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/convert-youtube" \
     -H "Content-Type: application/json" \
     -d '{"youtube_url": "https://www.youtube.com/watch?v=your_video_id"}' \
     --output youtube_podcast.mp3
```

## Project Structure

```
GoogleAudioPodcast/
├── src/
│   ├── api.py                  # FastAPI REST API server
│   ├── audio_processing.py     # Audio conversion and handling utilities
│   ├── podcast_generator.py    # Core Gemini TTS logic
│   └── youtube_utils.py        # YouTube download and transcription logic
├── cli.py                      # Unified command-line interface
├── requirements.txt            # Python dependencies
├── test_request.json           # Sample API request payload
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## Error Handling

The API includes comprehensive error handling for:
- Missing or invalid API keys
- Empty text input
- Audio generation failures
- Format conversion errors
- JSON validation errors

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source. Please check the license file for details.