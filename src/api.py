import io
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

from src.audio_processing import convert_wav_to_mp3
from src.podcast_generator import generate_podcast_audio
from src.youtube_utils import download_youtube_audio, transcribe_audio

load_dotenv()

app = FastAPI(title="Podcast Style Audio Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PodcastRequest(BaseModel):
    text: str

class YouTubeRequest(BaseModel):
    youtube_url: str

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle JSON validation errors with helpful messages."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid JSON format. Please ensure your JSON is properly formatted.",
            "errors": exc.errors(),
            "hint": "Common issues: escape newlines as \\n, escape quotes, and ensure proper JSON syntax"
        }
    )

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastRequest):
    """Generate a podcast audio file from text input."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    try:
        wav_audio = generate_podcast_audio(request.text)
        mp3_audio = convert_wav_to_mp3(wav_audio)

        return StreamingResponse(
            io.BytesIO(mp3_audio),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=podcast.mp3"}
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert-youtube")
async def convert_youtube_to_podcast(request: YouTubeRequest):
    """Convert a YouTube video to a podcast audio file."""
    if not request.youtube_url.strip():
        raise HTTPException(status_code=400, detail="YouTube URL cannot be empty")

    audio_file = None
    try:
        # 1. Download audio from YouTube
        audio_file = download_youtube_audio(request.youtube_url)

        # 2. Transcribe the audio
        transcription = transcribe_audio(audio_file)

        # 3. Generate podcast audio from transcription
        wav_audio = generate_podcast_audio(transcription)

        # 4. Convert WAV audio to MP3
        mp3_audio = convert_wav_to_mp3(wav_audio)

        # 5. Return the final MP3 file
        return StreamingResponse(
            io.BytesIO(mp3_audio),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=youtube_podcast.mp3"}
        )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # 6. Clean up temporary audio file
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status."""
    try:
        # Check if GEMINI_API_KEY is configured
        api_key = os.environ.get("GEMINI_API_KEY")
        api_key_configured = bool(api_key)

        return {
            "status": "healthy",
            "service": "Podcast Audio Generator API",
            "version": "1.0.0",
            "api_key_configured": api_key_configured
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Podcast Audio Generator API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)