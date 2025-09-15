# This file will contain the YouTube to podcast conversion workflow.
import os
import json
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

    # Convert to mono for compatibility with speech recognition
    print("Converting audio to mono...")
    audio = AudioSegment.from_wav(wav_path)
    mono_audio = audio.set_channels(1)  # Convert to mono
    mono_audio.export(mono_wav_path, format="wav")

    # Clean up original file
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
    return full_text

def generate_podcast(transcription: str) -> str:
    """
    Generates a podcast-style conversation from the given transcription.
    """
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    model = "gemini-1.5-flash"
    prompt = f"""
    Based on the following transcription, create a podcast-style conversation between two speakers.
    The conversation should be about the topic of the transcription.
    The output should be a single string with speakers identified as "Speaker 1:" and "Speaker 2:".

    Transcription:
    {transcription}
    """
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt)
            ],
        ),
    ]
    response = client.models.generate_content(
        model=model,
        contents=contents,
    )
    return response.text

def generate_podcast_from_youtube(url: str, output_file: str = None):
    """
    This function will take a YouTube URL, transcribe the audio, and generate a podcast-style conversation.
    Optionally saves the output to a file.
    """
    audio_file = download_youtube_audio(url)
    transcription = transcribe_audio(audio_file)
    # Clean up the audio file
    os.remove(audio_file)

    podcast_text = generate_podcast(transcription)

    output = {
        "text": podcast_text,
        "youtube_url": url,
        "generated_at": datetime.now().isoformat()
    }

    json_output = json.dumps(output, indent=2)

    # Save to file if output_file is specified
    if output_file:
        with open(output_file, 'w') as f:
            f.write(json_output)
        print(f"Output saved to: {output_file}")

    return json_output

if __name__ == '__main__':
    import sys

    # Check if URL is provided as command line argument
    if len(sys.argv) > 1:
        youtube_url = sys.argv[1]
        # Optional: specify output file as second argument
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Default example video
        youtube_url = "https://www.youtube.com/watch?v=G2yTKpUKXcI"  # Youtube video
        output_file = None

    # Generate default output filename if not specified
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"podcast_output_{timestamp}.json"

    print(f"Processing YouTube URL: {youtube_url}")
    print("This may take a few minutes...")

    try:
        podcast_json = generate_podcast_from_youtube(youtube_url, output_file)
        print("\n=== Generated Podcast ===")
        print(podcast_json)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
