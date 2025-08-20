from .edge_tts import EdgeTTSClient
from .openai_tts import OpenAITTSClient
from .tts_client import TTSClient

__all__ = [
    "EdgeTTSClient",
    "OpenAITTSClient",
    "TTSClient"
]


def get_tts_client(tts_vendor, character=None, **kwargs) -> TTSClient:
    if tts_vendor == 'edge':
        return EdgeTTSClient(character=character)
    elif tts_vendor == 'openai':
        # For OpenAI, character maps to voice parameter
        voice = character or kwargs.get('voice', 'alloy')
        model = kwargs.get('model', 'tts-1')
        instructions = kwargs.get('instructions', None)
        return OpenAITTSClient(voice=voice, model=model, instructions=instructions)
    else:
        raise ValueError(f"Unknown TTS vendor: {tts_vendor}")
