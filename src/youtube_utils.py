import os
import uuid
import tempfile
import yt_dlp
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
def download_youtube_audio(url: str) -> str:
    """
    Downloads the audio from a YouTube video and returns the path to the audio file.
    Ensures audio is converted to mono WAV format for compatibility with speech recognition.
    """
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
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
        raise ValueError(f"YouTube download failed: {str(e)}")

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
        temp_dir = tempfile.gettempdir()
        for i, audio_chunk in enumerate(chunks, start=1):
            chunk_filename = os.path.join(temp_dir, f"chunk{i}.wav")
            audio_chunk.export(chunk_filename, format="wav")

            try:
                with sr.AudioFile(chunk_filename) as source:
                    audio = r.record(source)
                    try:
                        text = r.recognize_sphinx(audio)
                        full_text += text + " "
                    except sr.UnknownValueError:
                        raise ValueError(f"Speech recognition could not understand audio in chunk {i}")
                    except sr.RequestError as e:
                        raise ValueError(f"Request error from speech recognition service: {e}")
            finally:
                if os.path.exists(chunk_filename):
                    os.remove(chunk_filename)

        transcription = full_text.strip()
        if not transcription or transcription == "[unintelligible]":
            raise ValueError("Could not transcribe audio, or audio was unintelligible")

        return transcription
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Transcription failed: {str(e)}")
