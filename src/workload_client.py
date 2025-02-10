import requests
from typing import Tuple, List


class WorkloadClientError(Exception):
    """Base class for workloads client exceptions."""
    pass


class WorkloadResponseError(WorkloadClientError):
    """Raised when the workloads backend returns an error response."""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Workload Error {status_code}: {message}")


class EasyVideoTransWorkloadClient:

    def __init__(
            self,
            audio_separation_endpoint="localhost:8199/audio_sep",
            audio_transcribe_endpoint="localhost:8199/audio-transcribe"
    ):
        self.audio_separation_endpoint = audio_separation_endpoint
        self.audio_transcribe_endpoint = audio_transcribe_endpoint

    def separate_audio(self, audio_filename: str) -> Tuple[str, str]:
        payload = {"file_name": audio_filename}

        response = requests.post(self.audio_separation_endpoint, json=payload, timeout=180)
        if response.status_code != 200:
            raise WorkloadResponseError(response.status_code, response.text)

        response_data = response.json()

        separated_files = response_data.get("files", [])
        if len(separated_files) != 2:
            raise WorkloadResponseError(500, "Invalid response format. Expected two separated files.")

        bg_filename, voice_filename = separated_files
        return bg_filename, voice_filename

    def transcribe_audio(self, audio_filename: str, output_filenames: List[str]) -> None:
        payload = {"file_name": audio_filename,
                   "output_filenames": output_filenames}

        response = requests.post(self.audio_transcribe_endpoint, json=payload, timeout=180)
        if response.status_code != 200:
            raise WorkloadResponseError(response.status_code, response.text)
