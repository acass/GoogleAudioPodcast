import argparse
import os
import sys
from datetime import datetime

# Add src to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.audio_processing import convert_wav_to_mp3
from src.podcast_generator import generate_podcast_audio
from src.youtube_utils import download_youtube_audio, transcribe_audio

def save_mp3_file(file_name: str, data: bytes):
    """Saves binary data to a file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")

def generate_from_text(args):
    """Generates a podcast from a text string or file."""
    print("Generating podcast from text...")
    if not args.text:
        # If no text is provided, use a default for demonstration
        text = "Speaker 1: Welcome to the show. Speaker 2: It's great to be here."
        print("No text provided. Using default text.")
    else:
        text = args.text

    if os.path.exists(text):
        print(f"Reading text from file: {text}")
        with open(text, 'r') as f:
            text = f.read()

    wav_audio = generate_podcast_audio(text)
    mp3_audio = convert_wav_to_mp3(wav_audio)

    output_file = args.output or f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    save_mp3_file(output_file, mp3_audio)
    print("Podcast generated successfully.")

def generate_from_youtube(args):
    """Generates a podcast from a YouTube URL."""
    print(f"Generating podcast from YouTube URL: {args.url}")
    audio_file = None
    try:
        audio_file = download_youtube_audio(args.url)
        print("Audio downloaded, now transcribing...")
        transcription = transcribe_audio(audio_file)
        print("Transcription complete, now generating podcast audio...")
        wav_audio = generate_podcast_audio(transcription)
        mp3_audio = convert_wav_to_mp3(wav_audio)

        output_file = args.output or f"youtube_podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        save_mp3_file(output_file, mp3_audio)
        print("Podcast generated successfully.")

    finally:
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)
            print(f"Cleaned up temporary file: {audio_file}")

def main():
    parser = argparse.ArgumentParser(description="Google Audio Podcast Generator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Sub-parser for generating from text
    parser_text = subparsers.add_parser("generate-text", help="Generate a podcast from text.")
    parser_text.add_argument("text", type=str, nargs='?', help="The text to generate the podcast from (can be a string or a filepath).")
    parser_text.add_argument("-o", "--output", type=str, help="The output MP3 file name.")
    parser_text.set_defaults(func=generate_from_text)

    # Sub-parser for generating from YouTube
    parser_youtube = subparsers.add_parser("generate-youtube", help="Generate a podcast from a YouTube URL.")
    parser_youtube.add_argument("url", type=str, help="The YouTube URL to process.")
    parser_youtube.add_argument("-o", "--output", type=str, help="The output MP3 file name.")
    parser_youtube.set_defaults(func=generate_from_youtube)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
