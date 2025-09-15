# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Google Audio Podcast generator that uses Google's Gemini API to create multi-speaker podcast episodes. The application generates realistic podcast-style conversations with different voices using Gemini's TTS (Text-to-Speech) capabilities. The project includes both a standalone script and a REST API for podcast generation.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install google-genai python-dotenv fastapi uvicorn pydub
```

### Running the Application
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Set up environment variables (copy .env.example to .env and add your Gemini API key)
cp .env.example .env
# Edit .env to add your actual GEMINI_API_KEY

# Run the standalone podcast generator
python app.py

# OR run the API server
python api.py
# Server will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## Architecture

### Core Components

- **app.py**: Standalone podcast generation script with file output
- **api.py**: FastAPI-based REST API server for podcast generation with HTTP endpoints
- **Audio Generation**: Uses Google Gemini 2.5 Pro Preview TTS model for multi-speaker audio
- **Voice Configuration**: Supports multiple speaker voices (Zephyr, Puck) for realistic conversations
- **Audio Processing**: Converts proprietary audio formats to WAV format with proper headers
- **Format Conversion**: API supports both WAV and MP3 output formats

### Key Functions

**app.py (Standalone Script)**
- `generate()` (app.py:20): Main generation function that configures Gemini client and processes streaming audio
- `save_binary_file()` (app.py:14): Saves generated audio chunks to disk
- `convert_to_wav()` (app.py:91): Converts raw audio data to WAV format with proper headers
- `parse_audio_mime_type()` (app.py:131): Extracts audio parameters from MIME type strings

**api.py (REST API)**
- `generate_podcast_audio()` (api.py:85): Core audio generation function using Gemini TTS
- `convert_wav_to_mp3()` (api.py:165): Converts WAV audio data to MP3 format using pydub
- `parse_audio_mime_type()` (api.py:31): Extracts audio parameters from MIME type strings
- `convert_to_wav()` (api.py:55): Generates WAV file headers for audio data

### Dependencies

- **google-genai**: Primary SDK for Google Gemini API integration
- **python-dotenv**: Environment variable management
- **fastapi**: Web framework for REST API functionality
- **uvicorn**: ASGI server for running FastAPI applications
- **pydub**: Audio format conversion and processing
- **Standard libraries**: base64, mimetypes, os, re, struct, io, tempfile for audio processing

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Required API key from Google AI Studio (https://makersuite.google.com/app/apikey)

### Audio Configuration
- Default sample rate: 24,000 Hz
- Default bits per sample: 16-bit
- Output format: WAV files
- Supported input formats: Various audio formats via MIME type detection

## API Endpoints

### POST /generate-podcast
Generates a podcast audio file from text input.

**Request Body:**
```json
{
  "text": "Speaker 1: Welcome to our podcast! Speaker 2: Thanks for having me!"
}
```

**Response:** Streaming MP3 audio file

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/generate-podcast" \
     -H "Content-Type: application/json" \
     -d '{"text": "Speaker 1: Hello! Speaker 2: Hi there!"}' \
     --output podcast.mp3
```

### GET /
Returns API information and documentation links.

## Generated Files

**Standalone Script (app.py):**
- Generates audio files with the pattern `tech_unraveled_podcast_{index}.wav` in the root directory

**API Server (api.py):**
- Returns MP3 audio as streaming response
- Example test file: `test_request.json` contains sample request payload