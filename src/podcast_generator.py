import os
from google import genai
from google.genai import types
from src.audio_processing import convert_to_wav

def generate_podcast_audio(text: str) -> bytes:
    """Generate podcast audio from text using Gemini TTS."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

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
            raise ValueError("No audio generated")

        combined_audio = b''.join(audio_chunks)

        if mime_type and "wav" not in mime_type.lower():
            combined_audio = convert_to_wav(combined_audio, mime_type)

        return combined_audio

    except Exception as e:
        raise ValueError(f"Audio generation failed: {str(e)}")
