import unittest
from unittest.mock import patch, MagicMock
from src.workload_client import EasyVideoTransWorkloadClient, WorkloadResponseError  # Import your class


class TestEasyVideoTransWorkloadClient(unittest.TestCase):

    def setUp(self):
        """Set up a test instance of the client."""
        self.client = EasyVideoTransWorkloadClient(
            audio_separation_endpoint="http://localhost:8199/audio-sep",
            audio_transcribe_endpoint="http://localhost:8199/audio-transcribe"
        )

    @patch("requests.post")
    def test_separate_audio_success(self, mock_post):
        """Test successful audio separation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": ["bg.wav", "voice.wav"]}
        mock_post.return_value = mock_response

        bg_file, voice_file = self.client.separate_audio("test_audio.wav")

        self.assertEqual(bg_file, "bg.wav")
        self.assertEqual(voice_file, "voice.wav")
        mock_post.assert_called_once_with(
            "http://localhost:8199/audio-sep",
            json={"file_name": "test_audio.wav"},
            timeout=120
        )

    @patch("requests.post")
    def test_separate_audio_error_response(self, mock_post):
        """Test error handling when API returns a non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with self.assertRaises(WorkloadResponseError) as context:
            self.client.separate_audio("test_audio.wav")

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.message, "Internal Server Error")

    @patch("requests.post")
    def test_separate_audio_invalid_response_format(self, mock_post):
        """Test handling when the API returns an unexpected response format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": ["bg.wav"]}  # Only one file instead of two
        mock_post.return_value = mock_response

        with self.assertRaises(WorkloadResponseError) as context:
            self.client.separate_audio("test_audio.wav")

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.message, "Invalid response format. Expected two separated files.")

    @patch("requests.post")
    def test_transcribe_audio_success(self, mock_post):
        """Test successful audio transcription."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.client.transcribe_audio("test_audio.wav", ["transcript.txt", "summary.txt"])

        mock_post.assert_called_once_with(
            "http://localhost:8199/audio-transcribe",
            json={"file_name": "test_audio.wav", "output_filenames": ["transcript.txt", "summary.txt"]},
            timeout=60
        )

    @patch("requests.post")
    def test_transcribe_audio_error_response(self, mock_post):
        """Test error handling when transcription API returns an error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with self.assertRaises(WorkloadResponseError) as context:
            self.client.transcribe_audio("test_audio.wav", ["transcript.txt"])

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, "Bad Request")


if __name__ == "__main__":
    unittest.main()
