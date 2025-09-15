import io
import os
import struct
import tempfile
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from pydub import AudioSegment
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

@app.get("/")
async def root():
    return {"message": "Podcast Audio Generator API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)