from .edge_tts import EdgeTTSClient
from .tts_client import TTSClient

__all__ = [
    "EdgeTTSClient",
    "TTSClient"
]


def get_tts_client(tts_vendor, character=None) -> TTSClient:
    if tts_vendor == 'edge':
        return EdgeTTSClient(character=character)
    else:
        raise ValueError("Unknown TTS vendor.")
