from abc import ABC, abstractmethod
from src.service.tts.edge_tts import EdgeTTSClient


class TTSClient(ABC):
    @abstractmethod
    def srt_to_voice(self, srt_file_path, output_dir):
        pass


def get_tts_client(tts_vendor, character=None) -> TTSClient:
    if tts_vendor == 'edge':
        return EdgeTTSClient(character=character)
    else:
        raise ValueError("Unknown TTS vendor.")
