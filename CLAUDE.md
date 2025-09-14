# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Google Audio Podcast generator that uses Google's Gemini API to create multi-speaker podcast episodes. The application generates realistic podcast-style conversations with different voices using Gemini's TTS (Text-to-Speech) capabilities.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install google-genai python-dotenv
```

### Running the Application
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Set up environment variables (copy .env.example to .env and add your Gemini API key)
cp .env.example .env
# Edit .env to add your actual GEMINI_API_KEY

# Run the podcast generator
python app.py
```

## Architecture

### Core Components

- **app.py**: Main application file containing the podcast generation logic
- **Audio Generation**: Uses Google Gemini 2.5 Pro Preview TTS model for multi-speaker audio
- **Voice Configuration**: Supports multiple speaker voices (Zephyr, Puck) for realistic conversations
- **Audio Processing**: Converts proprietary audio formats to WAV format with proper headers

### Key Functions

- `generate()` (app.py:20): Main generation function that configures Gemini client and processes streaming audio
- `save_binary_file()` (app.py:14): Saves generated audio chunks to disk
- `convert_to_wav()` (app.py:91): Converts raw audio data to WAV format with proper headers
- `parse_audio_mime_type()` (app.py:131): Extracts audio parameters from MIME type strings

### Dependencies

- **google-genai**: Primary SDK for Google Gemini API integration
- **python-dotenv**: Environment variable management
- **Standard libraries**: base64, mimetypes, os, re, struct for audio processing

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Required API key from Google AI Studio (https://makersuite.google.com/app/apikey)

### Audio Configuration
- Default sample rate: 24,000 Hz
- Default bits per sample: 16-bit
- Output format: WAV files
- Supported input formats: Various audio formats via MIME type detection

## Generated Files
The application generates audio files with the pattern `tech_unraveled_podcast_{index}.wav` in the root directory.