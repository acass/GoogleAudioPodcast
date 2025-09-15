import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json
import io

# Add the parent directory to sys.path to import api
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import app, PodcastRequest, parse_audio_mime_type, convert_to_wav

class TestPodcastAPI(unittest.TestCase):
    """Test cases for the Podcast Audio Generator API."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    # Test parse_audio_mime_type function
    def test_parse_audio_mime_type_with_rate(self):
        """Test parsing MIME type with rate parameter."""
        result = parse_audio_mime_type("audio/L16;rate=48000")
        self.assertEqual(result["bits_per_sample"], 16)
        self.assertEqual(result["rate"], 48000)
    
    def test_parse_audio_mime_type_without_rate(self):
        """Test parsing MIME type without rate parameter."""
        result = parse_audio_mime_type("audio/L16")
        self.assertEqual(result["bits_per_sample"], 16)
        self.assertEqual(result["rate"], 24000)  # Default rate
    
    def test_parse_audio_mime_type_with_different_bits(self):
        """Test parsing MIME type with different bits per sample."""
        result = parse_audio_mime_type("audio/L24;rate=44100")
        self.assertEqual(result["bits_per_sample"], 24)
        self.assertEqual(result["rate"], 44100)
    
    def test_parse_audio_mime_type_invalid_format(self):
        """Test parsing MIME type with invalid format."""
        result = parse_audio_mime_type("audio/wav")
        self.assertEqual(result["bits_per_sample"], 16)  # Default
        self.assertEqual(result["rate"], 24000)  # Default
    
    # Test convert_to_wav function
    def test_convert_to_wav_header_format(self):
        """Test WAV header generation."""
        audio_data = b'\x00\x01' * 100  # 200 bytes of audio data
        mime_type = "audio/L16;rate=24000"
        
        wav_data = convert_to_wav(audio_data, mime_type)
        
        # Check RIFF header
        self.assertEqual(wav_data[:4], b"RIFF")
        # Check WAVE format
        self.assertEqual(wav_data[8:12], b"WAVE")
        # Check fmt chunk
        self.assertEqual(wav_data[12:16], b"fmt ")
        # Check data chunk
        self.assertEqual(wav_data[36:40], b"data")
        # Check total size
        self.assertEqual(len(wav_data), 44 + 200)  # Header + audio data
    
    # Test root endpoint
    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Podcast Audio Generator API")
        self.assertEqual(data["docs"], "/docs")
    
    # Test health endpoint
    def test_health_endpoint(self):
        """Test health endpoint returns correct status."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self.client.get("/health")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertTrue(data["api_key_configured"])
    
    # Test generate-podcast endpoint
    def test_generate_podcast_empty_text(self):
        """Test that empty text returns 400 error."""
        response = self.client.post(
            "/generate-podcast",
            json={"text": ""}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Text input cannot be empty", response.json()["detail"])
    
    def test_generate_podcast_whitespace_only_text(self):
        """Test that whitespace-only text returns 400 error."""
        response = self.client.post(
            "/generate-podcast",
            json={"text": "   \n\t  "}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Text input cannot be empty", response.json()["detail"])
    
    def test_generate_podcast_no_api_key(self):
        """Test that missing API key returns 500 error."""
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                "/generate-podcast",
                json={"text": "Speaker 1: Hello"}
            )
            
            self.assertEqual(response.status_code, 500)
            self.assertIn("GEMINI_API_KEY not configured", response.json()["detail"])
    
    @patch('api.genai.Client')
    def test_generate_podcast_success(self, mock_client_class):
        """Test successful podcast generation."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the streaming response
        mock_chunk = MagicMock()
        mock_chunk.candidates = [MagicMock()]
        mock_chunk.candidates[0].content = MagicMock()
        mock_chunk.candidates[0].content.parts = [MagicMock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = MagicMock()
        mock_chunk.candidates[0].content.parts[0].inline_data.data = b'\x00\x01' * 100
        mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/L16;rate=24000"
        
        mock_client.models.generate_content_stream.return_value = [mock_chunk]
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self.client.post(
                "/generate-podcast",
                json={"text": "Speaker 1: Hello\nSpeaker 2: Hi there!"}
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "audio/mpeg")
            self.assertIn("filename=podcast.mp3", response.headers["content-disposition"])
    
    @patch('api.genai.Client')
    def test_generate_podcast_no_audio_chunks(self, mock_client_class):
        """Test handling when no audio chunks are generated."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock empty streaming response
        mock_client.models.generate_content_stream.return_value = []
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self.client.post(
                "/generate-podcast",
                json={"text": "Speaker 1: Hello"}
            )
            
            self.assertEqual(response.status_code, 500)
            self.assertIn("No audio generated", response.json()["detail"])
    
    # Test JSON validation error handling
    def test_invalid_json_format(self):
        """Test that invalid JSON returns helpful error message."""
        response = self.client.post(
            "/generate-podcast",
            data='{"text": "Invalid JSON}',  # Missing closing quote
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 422)
    
    def test_missing_required_field(self):
        """Test that missing required field returns validation error."""
        response = self.client.post(
            "/generate-podcast",
            json={}  # Missing 'text' field
        )
        
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("errors", data)
    
    def test_wrong_field_type(self):
        """Test that wrong field type returns validation error."""
        response = self.client.post(
            "/generate-podcast",
            json={"text": 123}  # Should be string, not number
        )
        
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("errors", data)
    
    # Test edge cases
    def test_very_long_text_input(self):
        """Test handling of very long text input."""
        long_text = "Speaker 1: " + "Hello world. " * 1000
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch('api.generate_podcast_audio') as mock_generate:
                mock_generate.return_value = b'WAV_DATA'
                with patch('api.convert_wav_to_mp3') as mock_convert:
                    mock_convert.return_value = b'MP3_DATA'
                    
                    response = self.client.post(
                        "/generate-podcast",
                        json={"text": long_text}
                    )
                    
                    # Should accept long text
                    self.assertEqual(response.status_code, 200)
    
    def test_special_characters_in_text(self):
        """Test handling of special characters in text."""
        special_text = 'Speaker 1: Hello! "How are you?" \n Speaker 2: I\'m fine, thanks!'
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch('api.generate_podcast_audio') as mock_generate:
                mock_generate.return_value = b'WAV_DATA'
                with patch('api.convert_wav_to_mp3') as mock_convert:
                    mock_convert.return_value = b'MP3_DATA'
                    
                    response = self.client.post(
                        "/generate-podcast",
                        json={"text": special_text}
                    )
                    
                    self.assertEqual(response.status_code, 200)
    
    # Test concurrent requests handling
    def test_multiple_requests_handling(self):
        """Test that API can handle multiple requests."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch('api.generate_podcast_audio') as mock_generate:
                mock_generate.return_value = b'WAV_DATA'
                with patch('api.convert_wav_to_mp3') as mock_convert:
                    mock_convert.return_value = b'MP3_DATA'
                    
                    # Send multiple requests
                    for i in range(3):
                        response = self.client.post(
                            "/generate-podcast",
                            json={"text": f"Speaker {i}: Test message {i}"}
                        )
                        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()