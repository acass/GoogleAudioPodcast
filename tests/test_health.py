import os
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api import app

class TestHealthEndpoint(unittest.TestCase):
    """Test cases for the health check endpoint."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint_with_api_key(self):
        """Test health endpoint when GEMINI_API_KEY is configured."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            response = self.client.get("/health")
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "Podcast Audio Generator API")
            self.assertEqual(data["version"], "1.0.0")
            self.assertTrue(data["api_key_configured"])
    
    def test_health_endpoint_without_api_key(self):
        """Test health endpoint when GEMINI_API_KEY is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove GEMINI_API_KEY if it exists
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]
            
            response = self.client.get("/health")
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "Podcast Audio Generator API")
            self.assertEqual(data["version"], "1.0.0")
            self.assertFalse(data["api_key_configured"])
    
    def test_health_endpoint_response_structure(self):
        """Test that health endpoint returns all expected fields."""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        expected_fields = ["status", "service", "version", "api_key_configured"]
        
        for field in expected_fields:
            self.assertIn(field, data, f"Missing field: {field}")
    
    def test_health_endpoint_method_not_allowed(self):
        """Test that POST method is not allowed on health endpoint."""
        response = self.client.post("/health")
        self.assertEqual(response.status_code, 405)
    
    def test_root_endpoint_still_works(self):
        """Test that the root endpoint still works after adding health endpoint."""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["message"], "Podcast Audio Generator API")
        self.assertEqual(data["docs"], "/docs")

if __name__ == "__main__":
    unittest.main()