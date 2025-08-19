import pytest
import numpy as np
import sys
from unittest.mock import patch, MagicMock

# Mock the heavy dependencies before importing inference
sys.modules['soundfile'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['workloads.lib.separator'] = MagicMock()
sys.modules['workloads.lib.spec_utils'] = MagicMock()
sys.modules['workloads.lib.nets'] = MagicMock()
sys.modules['workloads.lib.audio_processing.transcribe_audio'] = MagicMock()
sys.modules['workloads.lib.srt'] = MagicMock()

from inference import app  # noqa: E402


@pytest.fixture
def client():
    """Fixture to create a test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@patch("inference.os.path.exists", return_value=True)
@patch("inference.os.path.getsize", return_value=1024)  # Mock file size
@patch("inference.load_spectrogram", return_value=("mock_spectrogram", 44100))
@patch("inference.separator.separate_tta", return_value=("mock_bg_spec", "mock_v_spec"))
@patch("workloads.lib.spec_utils.spectrogram_to_wave", return_value=np.array([[0.1, 0.2], [0.3, 0.4]]))
@patch("inference.sf.write")  # Mock sound file write function
def test_audio_separation_success(mock_sf_write, mock_spec_to_wave, mock_separate, mock_load_spec, mock_getsize,
                                  mock_exists, client):
    """Test successful audio separation."""
    response = client.post("/audio-sep", json={"file_name": "audio.wav"})
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data and data["message"] == "Separation successful."
    assert "files" in data and len(data["files"]) == 2
    assert "inference_duration_seconds" in data
    assert "input_audio_size_bytes" in data and data["input_audio_size_bytes"] == 1024


def test_audio_separation_missing_file_path(client):
    """Test when 'file_path' is missing in the request."""
    response = client.post("/audio-sep", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data and "Invalid request" in data["error"]


@patch("inference.os.path.exists", return_value=False)
def test_audio_separation_file_not_found(mock_exists, client):
    """Test when the provided file path does not exist."""
    response = client.post("/audio-sep", json={"file_name": "invalid_path.wav"})
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data and "File not found" in data["error"]


@patch("inference.os.path.exists", return_value=True)
@patch("inference.os.path.getsize", return_value=100)
@patch("inference.load_spectrogram", side_effect=Exception("Spectrogram error"))
def test_audio_separation_internal_error(mock_load_spectrogram, mock_getsize, mock_exists, client):
    """Test when an internal error occurs during processing."""
    response = client.post("/audio-sep", json={"file_name": "audio.wav"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data and "An error occurred during audio separation." in data["error"]


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data and data["message"] == "Speech Separation API is running."
