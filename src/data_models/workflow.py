import json
import os


class Workflow:
    def __init__(self, params_dict=None):
        if params_dict is None:
            params_dict = {}

        self.proxy = params_dict.get("proxy", "127.0.0.1:7890")                         # 代理地址，留空则不使用代理
        self.video_id = params_dict.get("video Id", "")                                 # 油管视频ID
        self.work_path = params_dict.get("work path", "")                               # 工作目录
        self.download_video = params_dict.get("download video", False)                  # [工作流程开关]下载视频
        self.download_fhd_video = params_dict.get("download fhd video", False)          # [工作流程开关]下载1080p视频
        self.extract_audio = params_dict.get("extract audio", False)                    # [工作流程开关]提取音频
        self.audio_remove = params_dict.get("audio remove", False)                      # [工作流程开关]去除音乐
        self.audio_remove_model_path = params_dict.get("audio remove model path", "")   # 去音乐模型路径
        self.audio_transcribe = params_dict.get("audio transcribe", False)              # [工作流程开关]语音转文字
        self.audio_transcribe_model = params_dict.get("audio transcribe model", "")     # [工作流程开关]英文语音转文字模型名称
        self.srt_merge = params_dict.get("srt merge", False)                            # [工作流程开关]字幕合并
        self.srt_merge_en_to_text = params_dict.get("srt merge en to text", False)      # [工作流程开关]英文字幕转文字
        self.srt_merge_translate = params_dict.get("srt merge translate", False)        # [工作流程开关]字幕翻译
        self.srt_merge_translate_tool = params_dict.get("srt merge translate tool", "google")   # 翻译工具，目前支持google和deepl
        self.srt_merge_translate_key = params_dict.get("srt merge translate key", "")   # 翻译工具的key
        self.srt_merge_zh_to_text = params_dict.get("srt merge zh to text", False)      # [工作流程开关]中文字幕转文字
        self.srt_to_voice_source = params_dict.get("srt to voice srouce", False)        # [工作流程开关]字幕转语音
        self.TTS = params_dict.get("TTS", "edge")           # [工作流程开关]合成语音，目前支持edge、openai和GPT-SoVITS
        self.TTS_param = params_dict.get("TTS param", "")   # TTS参数，GPT-SoVITS为地址，edge为角色，openai为语音配置(JSON格式)。edge模式下可以不填，建议不要用GPT-SoVITS。
        self.voice_connect = params_dict.get("voice connect", False)                    # [工作流程开关]语音合并
        self.audio_zh_transcribe = params_dict.get("audio zh transcribe", False)        # [工作流程开关]合成后的语音转文字
        self.audio_zh_transcribe_model = params_dict.get("audio zh transcribe model", "medium")     # 中文语音转文字模型名称
        self.video_zh_preview = params_dict.get("video zh preview", False)              # [工作流程开关]视频预览

    def __repr__(self):
        return (
            f"<Workflow(proxy={self.proxy}, video_id={self.video_id}, "
            f"work_path={self.work_path}, download_video={self.download_video}, "
            f"download_fhd_video={self.download_fhd_video}, extract_audio={self.extract_audio}, "
            f"audio_remove={self.audio_remove}, audio_remove_model_path={self.audio_remove_model_path}, "
            f"audio_transcribe={self.audio_transcribe}, audio_transcribe_model={self.audio_transcribe_model}, "
            f"srt_merge={self.srt_merge}, srt_merge_en_to_text={self.srt_merge_en_to_text}, "
            f"srt_merge_translate={self.srt_merge_translate}, srt_merge_translate_tool={self.srt_merge_translate_tool}, "
            f"srt_merge_translate_key={self.srt_merge_translate_key}, srt_merge_zh_to_text={self.srt_merge_zh_to_text}, "
            f"srt_to_voice_source={self.srt_to_voice_source}, TTS={self.TTS}, TTS_param={self.TTS_param}, "
            f"voice_connect={self.voice_connect}, audio_zh_transcribe={self.audio_zh_transcribe}, "
            f"audio_zh_transcribe_model={self.audio_zh_transcribe_model}, video_zh_preview={self.video_zh_preview})"
        )

    def load_from_file(self, path):
        try:
            with open(path, 'r') as file:
                params_dict = json.load(file)
                self.__init__(params_dict)
        except FileNotFoundError:
            print(f"Error: File '{path}' not found.")
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from file '{path}'.")

    def write_to_file(self, path):
        params_dict = {
            "proxy": self.proxy,
            "video Id": self.video_id,
            "work path": self.work_path,
            "download video": self.download_video,
            "download fhd video": self.download_fhd_video,
            "extract audio": self.extract_audio,
            "audio remove": self.audio_remove,
            "audio remove model path": self.audio_remove_model_path,
            "audio transcribe": self.audio_transcribe,
            "audio transcribe model": self.audio_transcribe_model,
            "srt merge": self.srt_merge,
            "srt merge en to text": self.srt_merge_en_to_text,
            "srt merge translate": self.srt_merge_translate,
            "srt merge translate tool": self.srt_merge_translate_tool,
            "srt merge translate key": self.srt_merge_translate_key,
            "srt merge zh to text": self.srt_merge_zh_to_text,
            "srt to voice srouce": self.srt_to_voice_source,
            "TTS": self.TTS,
            "TTS param": self.TTS_param,
            "voice connect": self.voice_connect,
            "audio zh transcribe": self.audio_zh_transcribe,
            "audio zh transcribe model": self.audio_zh_transcribe_model,
            "video zh preview": self.video_zh_preview
        }

        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)

            with open(path, 'w') as file:
                json.dump(params_dict, file, indent=4)
        except IOError:
            print(f"Error: Failed to write to file '{path}'.")


if __name__ == '__main__':
    paramDirPathAndName = input("json file path or press enter to skip\n")
    print(paramDirPathAndName)
    print(paramDirPathAndName is None)
    print(paramDirPathAndName == "")
