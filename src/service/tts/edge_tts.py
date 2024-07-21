import os
import copy
import asyncio
import srt
import edge_tts
import tenacity
from pydub import AudioSegment
from src.service.tts.tts_client import TTSClient


class EdgeTTSClient(TTSClient):
    def __init__(self, character="zh-CN-XiaoyiNeural"):
        self.character = character

    async def _convert_srt_to_voice_edge(self, text, path):
        communicate = edge_tts.Communicate(text, self.character)
        await communicate.save(path)

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

        coroutines = []
        for index, sub_title in enumerate(sub_title_list, start=1):
            file_mp3_name = f"{index}.mp3"
            file_name = f"{index}.wav"
            output_mp3_path = os.path.join(output_dir, file_mp3_name)
            file_mp3_names.append(file_mp3_name)
            file_names.append(file_name)
            coroutines.append(self._convert_srt_to_voice_edge(sub_title.content, output_mp3_path))

        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*coroutines))

        print("\nConvert srt to mp3 voice successfully!!!")
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

        print("Converted srt to wav voice successfully")
        return True
