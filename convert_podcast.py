import io
import os
import struct
import tempfile
import uuid
import yt_dlp
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Functions from youtube_convert.py ---

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

    print("Downloading audio from YouTube...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print("Converting audio to mono...")
    audio = AudioSegment.from_wav(wav_path)
    mono_audio = audio.set_channels(1)
    mono_audio.export(mono_wav_path, format="wav")

    os.remove(wav_path)
    return mono_wav_path

def transcribe_audio(audio_file: str) -> str:
    """
    Transcribes the given audio file and returns the text.
    """
    r = sr.Recognizer()
    sound = AudioSegment.from_wav(audio_file)
    chunks = split_on_silence(sound,
        min_silence_len = 500,
        silence_thresh = sound.dBFS-14,
        keep_silence=500,
    )
    full_text = ""
    print("Transcribing audio...")
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = f"/tmp/chunk{i}.wav"
        audio_chunk.export(chunk_filename, format="wav")
        with sr.AudioFile(chunk_filename) as source:
            audio = r.record(source)
            try:
                text = r.recognize_sphinx(audio)
                full_text += text + " "
            except sr.UnknownValueError:
                full_text += "[unintelligible] "
            except sr.RequestError as e:
                full_text += f"[request error: {e}] "
        os.remove(chunk_filename)
    return full_text.strip()

# --- Functions from api.py (adapted for script use) ---

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
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

def generate_podcast_audio(text: str) -> bytes:
    """Generate podcast audio from text using Gemini TTS."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured in .env file")

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-pro-preview-tts"
    prompt = f"Please read aloud the following in a podcast interview style:\n{text}"
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(speaker="Speaker 1", voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr"))),
                    types.SpeakerVoiceConfig(speaker="Speaker 2", voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck"))),
                ]
            )
        ),
    )

    audio_chunks = []
    mime_type = None
    print("Generating podcast audio...")
    try:
        for chunk in client.models.generate_content_stream(model=model, contents=contents, config=generate_content_config):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    audio_chunks.append(inline_data.data)
                    if mime_type is None:
                        mime_type = inline_data.mime_type
        if not audio_chunks:
            raise RuntimeError("No audio generated")
        combined_audio = b''.join(audio_chunks)
        if mime_type and "wav" not in mime_type.lower():
            combined_audio = convert_to_wav(combined_audio, mime_type)
        return combined_audio
    except Exception as e:
        raise RuntimeError(f"Audio generation failed: {str(e)}")

def convert_wav_to_mp3(wav_data: bytes) -> bytes:
    """Convert WAV audio data to MP3 format."""
    print("Converting audio to MP3...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_file.write(wav_data)
            wav_path = wav_file.name

        audio = AudioSegment.from_wav(wav_path)
        mp3_buffer = io.BytesIO()
        audio.export(mp3_buffer, format="mp3")
        mp3_buffer.seek(0)

        os.remove(wav_path)
        return mp3_buffer.read()
    except Exception as e:
        raise RuntimeError(f"MP3 conversion failed: {str(e)}")

def youtube_to_podcast_conversion(youtube_url: str, output_file: str):
    """
    Orchestrates the conversion of a YouTube video to a podcast audio file.
    """
    audio_file = None
    try:
        # 1. Download audio from YouTube
        audio_file = download_youtube_audio(youtube_url)

        # 2. Transcribe the audio
        transcription = transcribe_audio(audio_file)
        if not transcription or transcription == "[unintelligible]":
            print("Could not transcribe audio, or audio was unintelligible. Aborting.")
            return

        print("\n--- Transcription ---")
        print(transcription)
        print("---------------------\n")

        # 3. Generate podcast audio from transcription
        wav_audio = generate_podcast_audio(transcription)

        # 4. Convert WAV audio to MP3
        mp3_audio = convert_wav_to_mp3(wav_audio)

        # 5. Save the final MP3 file
        with open(output_file, 'wb') as f:
            f.write(mp3_audio)

        print(f"\nSuccessfully created podcast and saved to: {output_file}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 6. Clean up temporary audio file
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)
            print(f"Cleaned up temporary file: {audio_file}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python convert_podcast.py <youtube_url> [output_file.mp3]")
        sys.exit(1)

    youtube_url = sys.argv[1]

    # Generate default output filename if not specified
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"podcast_output_{timestamp}.mp3"

    print(f"Processing YouTube URL: {youtube_url}")
    print("This may take a few minutes...")

    youtube_to_podcast_conversion(youtube_url, output_file)
