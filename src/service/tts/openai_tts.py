import os
import copy
import srt
import tenacity
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from src.service.tts.tts_client import TTSClient


class OpenAITTSClient(TTSClient):
    def __init__(self, voice="alloy", model="tts-1", instructions=None):
        """
        Initialize OpenAI TTS client.

        Args:
            voice: OpenAI voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: OpenAI TTS model (tts-1 or tts-1-hd)
            instructions: Optional instructions for voice tone/style
        """
        # Get OpenAI API key from environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI TTS")

        # Create OpenAI client with only the API key
        self.client = OpenAI(api_key=api_key)
        self.voice = voice
        self.model = model
        self.instructions = instructions

    def _convert_text_to_voice_openai(self, text, output_path):
        """Convert text to speech using OpenAI TTS API."""
        speech_file_path = Path(output_path)

        # Create the speech request
        kwargs = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
        }

        # Add instructions if provided
        if self.instructions:
            kwargs["instructions"] = self.instructions

        with self.client.audio.speech.with_streaming_response.create(**kwargs) as response:
            response.stream_to_file(speech_file_path)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def srt_to_voice(self, srt_file_path, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(srt_file_path, "r", encoding="utf-8") as file:
            srt_content = file.read()

        sub_generator = srt.parse(srt_content)
        sub_title_list = list(sub_generator)
        file_mp3_names = []
        file_names = []

        try:
            for index, sub_title in enumerate(sub_title_list, start=1):
                file_mp3_name = f"{index}.mp3"
                file_name = f"{index}.wav"
                output_mp3_path = os.path.join(output_dir, file_mp3_name)
                file_mp3_names.append(file_mp3_name)
                file_names.append(file_name)

                # Convert text to speech using OpenAI
                self._convert_text_to_voice_openai(sub_title.content, output_mp3_path)

            print("convert srt to mp3 voice using OpenAI successfully")
        except Exception as e:
            print(f"convert srt to mp3 voice using OpenAI exception: {e}")
            raise

        # Convert MP3 to WAV files
        for mp3_file_name, wav_file_name in zip(file_mp3_names, file_names):
            mp3_path = os.path.join(output_dir, mp3_file_name)
            wav_path = os.path.join(output_dir, wav_file_name)
            sound = AudioSegment.from_mp3(mp3_path)
            sound.export(wav_path, format="wav")
            os.remove(mp3_path)

        print("Converted to wav successfully")
        voice_map_srt = copy.deepcopy(sub_title_list)
        for i, sub_title in enumerate(voice_map_srt):
            sub_title.content = file_names[i]

        voice_map_srt_content = srt.compose(voice_map_srt)
        voice_map_srt_path = os.path.join(output_dir, "voiceMap.srt")
        with open(voice_map_srt_path, "w", encoding="utf-8") as file:
            file.write(voice_map_srt_content)

        srt_additional_path = os.path.join(output_dir, "sub.srt")
        with open(srt_additional_path, "w", encoding="utf-8") as file:
            file.write(srt_content)

        print("Converted srt to wav voice using OpenAI successfully")
        return True
