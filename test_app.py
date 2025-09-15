import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile

# Add the parent directory to sys.path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import save_binary_file, parse_audio_mime_type, convert_to_wav, generate

class TestPodcastApp(unittest.TestCase):
    """Test cases for the standalone podcast generator app."""
    
    # Test save_binary_file function
    def test_save_binary_file(self):
        """Test saving binary data to file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            test_data = b'Test binary data'
            save_binary_file(tmp_file.name, test_data)
            
            # Read back the file to verify
            with open(tmp_file.name, 'rb') as f:
                saved_data = f.read()
            
            self.assertEqual(saved_data, test_data)
            
            # Clean up
            os.unlink(tmp_file.name)
    
    @patch('builtins.print')
    def test_save_binary_file_prints_message(self, mock_print):
        """Test that save_binary_file prints confirmation message."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            save_binary_file(tmp_file.name, b'data')
            mock_print.assert_called_with(f"File saved to: {tmp_file.name}")
            os.unlink(tmp_file.name)
    
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
    
    def test_parse_audio_mime_type_with_L24(self):
        """Test parsing MIME type with L24 format."""
        result = parse_audio_mime_type("audio/L24;rate=44100")
        self.assertEqual(result["bits_per_sample"], 24)
        self.assertEqual(result["rate"], 44100)
    
    def test_parse_audio_mime_type_invalid_format(self):
        """Test parsing MIME type with invalid format."""
        result = parse_audio_mime_type("audio/wav")
        self.assertEqual(result["bits_per_sample"], 16)  # Default
        self.assertEqual(result["rate"], 24000)  # Default
    
    def test_parse_audio_mime_type_malformed_rate(self):
        """Test parsing MIME type with malformed rate."""
        result = parse_audio_mime_type("audio/L16;rate=invalid")
        self.assertEqual(result["bits_per_sample"], 16)
        self.assertEqual(result["rate"], 24000)  # Default when parsing fails
    
    def test_parse_audio_mime_type_empty_rate(self):
        """Test parsing MIME type with empty rate value."""
        result = parse_audio_mime_type("audio/L16;rate=")
        self.assertEqual(result["bits_per_sample"], 16)
        self.assertEqual(result["rate"], 24000)  # Default when parsing fails
    
    # Test convert_to_wav function
    def test_convert_to_wav_header_structure(self):
        """Test WAV header generation structure."""
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
    
    def test_convert_to_wav_different_sample_rates(self):
        """Test WAV conversion with different sample rates."""
        audio_data = b'\x00' * 100
        
        # Test 44100 Hz
        wav_data_44100 = convert_to_wav(audio_data, "audio/L16;rate=44100")
        self.assertEqual(len(wav_data_44100), 44 + 100)
        
        # Test 48000 Hz
        wav_data_48000 = convert_to_wav(audio_data, "audio/L16;rate=48000")
        self.assertEqual(len(wav_data_48000), 44 + 100)
    
    def test_convert_to_wav_different_bit_depths(self):
        """Test WAV conversion with different bit depths."""
        audio_data = b'\x00' * 100
        
        # Test 16-bit
        wav_data_16 = convert_to_wav(audio_data, "audio/L16;rate=24000")
        self.assertEqual(len(wav_data_16), 44 + 100)
        
        # Test 24-bit
        wav_data_24 = convert_to_wav(audio_data, "audio/L24;rate=24000")
        self.assertEqual(len(wav_data_24), 44 + 100)
    
    # Test generate function
    @patch('app.genai.Client')
    @patch('app.save_binary_file')
    @patch('builtins.print')
    def test_generate_success(self, mock_print, mock_save, mock_client_class):
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
            generate()
            
            # Verify save_binary_file was called
            mock_save.assert_called_once()
            # Verify completion message was printed
            mock_print.assert_any_call("Created complete podcast with 1 audio chunks")
    
    @patch('app.genai.Client')
    @patch('builtins.print')
    def test_generate_no_audio_chunks(self, mock_print, mock_client_class):
        """Test handling when no audio chunks are received."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock empty streaming response
        mock_client.models.generate_content_stream.return_value = []
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generate()
            
            # Verify "No audio chunks received" message
            mock_print.assert_called_with("No audio chunks received")
    
    @patch('app.genai.Client')
    @patch('app.save_binary_file')
    @patch('builtins.print')
    def test_generate_multiple_chunks(self, mock_print, mock_save, mock_client_class):
        """Test handling multiple audio chunks."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock multiple chunks
        chunks = []
        for i in range(5):
            mock_chunk = MagicMock()
            mock_chunk.candidates = [MagicMock()]
            mock_chunk.candidates[0].content = MagicMock()
            mock_chunk.candidates[0].content.parts = [MagicMock()]
            mock_chunk.candidates[0].content.parts[0].inline_data = MagicMock()
            mock_chunk.candidates[0].content.parts[0].inline_data.data = b'\x00\x01' * 20
            mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/L16;rate=24000"
            chunks.append(mock_chunk)
        
        mock_client.models.generate_content_stream.return_value = chunks
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generate()
            
            # Verify all chunks were processed
            mock_print.assert_any_call("Created complete podcast with 5 audio chunks")
    
    @patch('app.genai.Client')
    @patch('app.save_binary_file')
    def test_generate_with_unknown_mime_type(self, mock_save, mock_client_class):
        """Test handling unknown MIME type (should convert to WAV)."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock chunk with unknown MIME type
        mock_chunk = MagicMock()
        mock_chunk.candidates = [MagicMock()]
        mock_chunk.candidates[0].content = MagicMock()
        mock_chunk.candidates[0].content.parts = [MagicMock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = MagicMock()
        mock_chunk.candidates[0].content.parts[0].inline_data.data = b'\x00\x01' * 100
        mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/unknown"
        
        mock_client.models.generate_content_stream.return_value = [mock_chunk]
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch('app.mimetypes.guess_extension', return_value=None):
                generate()
                
                # Verify file was saved with .wav extension
                saved_filename = mock_save.call_args[0][0]
                self.assertTrue(saved_filename.endswith('.wav'))
    
    @patch('app.genai.Client')
    @patch('builtins.print')
    def test_generate_with_text_response(self, mock_print, mock_client_class):
        """Test handling when chunk contains text instead of audio."""
        # Mock the Gemini client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock chunk with text
        mock_chunk = MagicMock()
        mock_chunk.candidates = [MagicMock()]
        mock_chunk.candidates[0].content = MagicMock()
        mock_chunk.candidates[0].content.parts = [MagicMock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = None
        mock_chunk.text = "Some text response"
        
        mock_client.models.generate_content_stream.return_value = [mock_chunk]
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generate()
            
            # Verify text was printed
            mock_print.assert_any_call("Some text response")
    
    def test_generate_without_api_key(self):
        """Test that generate raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Exception):
                generate()
    
    @patch('app.genai.Client')
    def test_generate_with_api_error(self, mock_client_class):
        """Test handling API errors during generation."""
        # Mock the Gemini client to raise an exception
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content_stream.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(Exception) as context:
                generate()
            self.assertIn("API Error", str(context.exception))

if __name__ == "__main__":
    unittest.main()