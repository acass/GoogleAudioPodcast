import io
import os
import struct
import tempfile
import uuid
from typing import Optional

import yt_dlp
import speech_recognition as sr
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from pydub import AudioSegment
from pydub.silence import split_on_silence
from dotenv import load_dotenv
from google import genai
from google.genai import types

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

def download_youtube_audio(url: str) -> str:
    """
    Downloads the audio from a YouTube video and returns the path to the audio file.
    Ensures audio is converted to mono WAV format for compatibility with speech recognition.
    """
    video_path = f"/tmp/{uuid.uuid4()}.mp4"
    wav_path = f"{video_path}.wav"
    mono_wav_path = f"{video_path}_mono.wav"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': video_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        audio = AudioSegment.from_wav(wav_path)
        mono_audio = audio.set_channels(1)
        mono_audio.export(mono_wav_path, format="wav")

        os.remove(wav_path)
        return mono_wav_path
    except Exception as e:
        # Clean up any partial files
        for path in [video_path, wav_path, mono_wav_path]:
            if os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=500, detail=f"YouTube download failed: {str(e)}")

def transcribe_audio(audio_file: str) -> str:
    """
    Transcribes the given audio file and returns the text.
    """
    r = sr.Recognizer()
    sound = AudioSegment.from_wav(audio_file)
    chunks = split_on_silence(sound,
        min_silence_len=500,
        silence_thresh=sound.dBFS-14,
        keep_silence=500,
    )
    full_text = ""

    try:
        for i, audio_chunk in enumerate(chunks, start=1):
            chunk_filename = f"/tmp/chunk{i}.wav"
            audio_chunk.export(chunk_filename, format="wav")

            try:
                with sr.AudioFile(chunk_filename) as source:
                    audio = r.record(source)
                    try:
                        text = r.recognize_sphinx(audio)
                        full_text += text + " "
                    except sr.UnknownValueError:
                        full_text += "[unintelligible] "
                    except sr.RequestError as e:
                        full_text += f"[request error: {e}] "
            finally:
                if os.path.exists(chunk_filename):
                    os.remove(chunk_filename)

        transcription = full_text.strip()
        if not transcription or transcription == "[unintelligible]":
            raise HTTPException(status_code=422, detail="Could not transcribe audio, or audio was unintelligible")

        return transcription
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass

    main_type = parts[0].strip()
    if "L" in main_type:
        try:
            bits_per_sample = int(main_type.split("L", 1)[1])
        except (ValueError, IndexError):
            pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data

def generate_podcast_audio(text: str) -> bytes:
    """Generate podcast audio from text using Gemini TTS."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-pro-preview-tts"

    prompt = f"Please read aloud the following in a podcast interview style:\n{text}"

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 1",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 2",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Puck"
                            )
                        ),
                    ),
                ]
            ),
        ),
    )

    audio_chunks = []
    mime_type = None

    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue

            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_chunks.append(inline_data.data)
                if mime_type is None:
                    mime_type = inline_data.mime_type

        if not audio_chunks:
            raise HTTPException(status_code=500, detail="No audio generated")

        combined_audio = b''.join(audio_chunks)

        if mime_type and "wav" not in mime_type.lower():
            combined_audio = convert_to_wav(combined_audio, mime_type)

        return combined_audio

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

def convert_wav_to_mp3(wav_data: bytes) -> bytes:
    """Convert WAV audio data to MP3 format."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            wav_file.write(wav_data)
            wav_file.flush()

            audio = AudioSegment.from_wav(wav_file.name)

            mp3_buffer = io.BytesIO()
            audio.export(mp3_buffer, format="mp3")
            mp3_buffer.seek(0)

            return mp3_buffer.read()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MP3 conversion failed: {str(e)}")

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

    wav_audio = generate_podcast_audio(request.text)
    mp3_audio = convert_wav_to_mp3(wav_audio)

    return StreamingResponse(
        io.BytesIO(mp3_audio),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=podcast.mp3"}
    )

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube to podcast conversion failed: {str(e)}")
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