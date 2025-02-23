import pytest
import numpy as np
from unittest.mock import patch, Mock

from inference import app, perform_separation, spec_utils


@pytest.fixture
def client():
    """Fixture to create a test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data and data["message"] == "Speech Separation API is running."


@patch("inference.os.path.exists", return_value=True)
@patch("inference.task_scheduler.add_task", return_value="test_task_id")
def test_submit_audio_separation_success(mock_add_task, mock_exists, client):
    """Test successful submission of audio separation task."""
    response = client.post("/audio-sep", json={"file_name": "test.wav"})
    assert response.status_code == 202
    data = response.get_json()
    assert "message" in data and data["message"] == "Task submitted successfully"
    assert "task_id" in data and data["task_id"] == "test_task_id"
    mock_add_task.assert_called_once()


@patch("inference.os.path.exists", return_value=True)
@patch(
    "inference.task_scheduler.add_task", side_effect=Exception("Task submission failed")
)
def test_submit_audio_separation_failure(mock_add_task, mock_exists, client):
    """Test failed submission of audio separation task."""
    response = client.post("/audio-sep", json={"file_name": "test.wav"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "Failed to submit task" in data["error"]


def test_submit_audio_separation_invalid_json(client):
    """Test submitting audio separation with invalid JSON."""
    response = client.post("/audio-sep", data="invalid json")
    assert response.status_code == 400
    data = response.get_json()
    assert "message" in data
    assert "Missing JSON in request" == data["message"]


@patch("inference.sf.write")
@patch("inference.spec_utils.spectrogram_to_wave")
@patch("inference.separator.separate_tta")
@patch("inference.load_spectrogram")
@patch("inference.torch.cuda.is_available", return_value=True)
@patch("inference.os.path.getsize", return_value=1024)
@patch("inference.os.path.exists", return_value=True)
def test_perform_separation_success(
    mock_exists,
    mock_getsize,
    mock_cuda,
    mock_load_spec,
    mock_separate,
    mock_spec_to_wave,
    mock_sf_write,
):
    """Test successful audio separation processing."""
    # Setup mocks
    mock_load_spec.return_value = (np.array([[0.1, 0.2]]), 44100)
    mock_separate.return_value = (
        np.array([[0.1, 0.2]]),  # instrumentals
        np.array([[0.3, 0.4]]),  # vocals
    )
    mock_spec_to_wave.return_value = np.array([[0.1, 0.2]])

    result = perform_separation("test.wav")

    assert isinstance(result, dict)
    assert "files" in result
    assert len(result["files"]) == 2
    assert "inference_duration_seconds" in result
    assert "input_audio_size_bytes" in result
    assert result["input_audio_size_bytes"] == 1024
    mock_separate.assert_called_once()
    mock_sf_write.assert_called()
    assert mock_sf_write.call_count == 2


@patch("inference.os.path.exists", return_value=True)
@patch("inference.os.path.getsize", return_value=1024)
@patch("inference.load_spectrogram")
def test_perform_separation_load_error(mock_load_spec, mock_getsize, mock_exists):
    """Test audio separation when loading audio fails."""
    mock_load_spec.side_effect = Exception("Failed to load audio")

    with pytest.raises(Exception) as exc_info:
        perform_separation("test.wav")
    assert "Failed to load audio" in str(exc_info.value)


@patch("inference.os.path.exists", return_value=True)
@patch("inference.os.path.getsize", return_value=1024)
@patch("inference.load_spectrogram")
@patch("inference.separator.separate_tta")
def test_perform_separation_model_error(
    mock_separate, mock_load_spec, mock_getsize, mock_exists
):
    """Test audio separation when model processing fails."""
    mock_load_spec.return_value = (np.array([[0.1, 0.2]]), 44100)
    mock_separate.side_effect = Exception("Model processing failed")

    with pytest.raises(Exception) as exc_info:
        perform_separation("test.wav")
    assert "Model processing failed" in str(exc_info.value)


@patch("inference.os.path.exists", return_value=False)
def test_perform_separation_file_not_found(mock_exists):
    """Test audio separation when input file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        perform_separation("nonexistent.wav")
