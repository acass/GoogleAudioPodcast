# This file will contain the YouTube to podcast conversion workflow.
import os
import json
import uuid
import yt_dlp
import speech_recognition as sr
import moviepy.editor as mp
import moviepy

def download_youtube_audio(url: str) -> str:
    """
    Downloads the audio from a YouTube video and returns the path to the audio file.
    """
    video_path = f"/tmp/{uuid.uuid4()}.mp4"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': video_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return f"{video_path}.wav"

from pydub import AudioSegment
from pydub.silence import split_on_silence

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

from google import genai
from google.genai import types

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

def generate_podcast_from_youtube(url: str):
    """
    This function will take a YouTube URL, transcribe the audio, and generate a podcast-style conversation.
    """
    audio_file = download_youtube_audio(url)
    transcription = transcribe_audio(audio_file)
    # Clean up the audio file
    os.remove(audio_file)

    podcast_text = generate_podcast(transcription)

    output = {
        "text": podcast_text
    }

    return json.dumps(output, indent=2)

if __name__ == '__main__':
    # Example usage:
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    podcast_json = generate_podcast_from_youtube(youtube_url)
    print(podcast_json)
    pass
