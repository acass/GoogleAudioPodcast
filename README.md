# Google Audio Podcast Generator

A powerful Python application that generates realistic podcast-style conversations using Google's Gemini 2.5 Pro Preview TTS (Text-to-Speech) model. Create multi-speaker audio content with distinct voices for engaging podcast episodes.

## Features

- **Multi-Speaker TTS**: Generate conversations with multiple distinct voices (Zephyr, Puck)
- **Dual Interface**: Both standalone script and REST API server
- **Audio Format Support**: Outputs WAV and MP3 formats with proper audio headers
- **Streaming Audio**: Real-time audio generation and streaming responses
- **Voice Configuration**: Configurable speaker voices for realistic conversations
- **CORS Support**: Web-friendly API with cross-origin resource sharing

## Prerequisites

- Python 3.7 or higher
- Google Gemini API key (get yours at [Google AI Studio](https://makersuite.google.com/app/apikey))

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GoogleAudioPodcast
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # .venv\Scripts\activate   # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install google-genai python-dotenv fastapi uvicorn pydub
   ```

## Configuration

1. **Set up environment variables**
   ```bash
   # Create .env file in project root
   echo "GEMINI_API_KEY=your_actual_api_key_here" > .env
   ```

2. **Get your Gemini API key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create or select a project
   - Generate an API key
   - Add it to your `.env` file

## Usage

### Standalone Script

Generate a podcast audio file directly to disk:

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Run the standalone generator
python app.py
```

The script will generate a file named `tech_unraveled_podcast.wav` in the project directory.

### REST API Server

Start the API server for HTTP-based podcast generation:

```bash
# Start the API server
python api.py
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

# Using the provided test file
curl -X POST "http://localhost:8000/generate-podcast" \
     -H "Content-Type: application/json" \
     -d @test_request.json \
     --output podcast.mp3
```

### GET /

Returns API information and links to documentation.

**Response:**
```json
{
  "message": "Podcast Audio Generator API",
  "docs": "/docs"
}
```

## Project Structure

```
GoogleAudioPodcast/
├── app.py              # Standalone podcast generation script
├── api.py              # FastAPI REST API server
├── test_request.json   # Sample API request payload
├── .env               # Environment variables (create this)
└── README.md          # This file
```

### Key Components

- **app.py**: Standalone script with file output
  - `generate()` - Main generation function
  - `save_binary_file()` - Saves audio chunks to disk
  - `convert_to_wav()` - Converts audio to WAV format

- **api.py**: FastAPI-based REST API
  - `generate_podcast_audio()` - Core audio generation
  - `convert_wav_to_mp3()` - MP3 format conversion
  - `parse_audio_mime_type()` - Audio parameter extraction

## Dependencies

- **google-genai**: Google Gemini API SDK for TTS functionality
- **python-dotenv**: Environment variable management
- **fastapi**: Modern web framework for the REST API
- **uvicorn**: ASGI server for running FastAPI applications
- **pydub**: Audio format conversion and processing

## Audio Configuration

- **Sample Rate**: 24,000 Hz (default)
- **Bit Depth**: 16-bit (default)
- **Channels**: Mono (1 channel)
- **Output Formats**: WAV (standalone), MP3 (API)
- **Voice Options**: Zephyr, Puck (configurable in speaker configs)

## Examples

### Sample Podcast Text Format

Structure your text with speaker labels for best results:

```
Speaker 1: Welcome to Tech Unraveled, the podcast where we explore the future of technology.
Speaker 2: That's right! Today we're discussing artificial intelligence and its impact on creative industries.
Speaker 1: It's fascinating how AI is transforming content creation.
Speaker 2: Absolutely, and that's exactly what we'll be diving into today.
```

### Programmatic API Usage (Python)

```python
import requests

url = "http://localhost:8000/generate-podcast"
payload = {
    "text": "Speaker 1: Welcome to our show! Speaker 2: Thanks for having me!"
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    with open("my_podcast.mp3", "wb") as f:
        f.write(response.content)
    print("Podcast generated successfully!")
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

## Support

For issues and questions:
- Check the [API documentation](http://localhost:8000/docs) when running the server
- Review the sample `test_request.json` for proper request formatting
- Ensure your Gemini API key is properly configured

## Acknowledgments

- Built with Google's Gemini 2.5 Pro Preview TTS model
- Powered by FastAPI for robust API functionality
- Audio processing via pydub library