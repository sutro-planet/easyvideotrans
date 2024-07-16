import json


class WorkflowParams:
    def __init__(self, params_dict=None):
        if params_dict is None:
            params_dict = {}

        self.proxy = params_dict.get("proxy", "127.0.0.1:7890")
        self.video_id = params_dict.get("video Id", "")
        self.work_path = params_dict.get("work path", "")
        self.download_video = params_dict.get("download video", False)
        self.download_fhd_video = params_dict.get("download fhd video", False)
        self.extract_audio = params_dict.get("extract audio", False)
        self.audio_remove = params_dict.get("audio remove", False)
        self.audio_remove_model_path = params_dict.get("audio remove model path", "")
        self.audio_transcribe = params_dict.get("audio transcribe", False)
        self.audio_transcribe_model = params_dict.get("audio transcribe model", "")
        self.srt_merge = params_dict.get("srt merge", False)
        self.srt_merge_en_to_text = params_dict.get("srt merge en to text", False)
        self.srt_merge_translate = params_dict.get("srt merge translate", False)
        self.srt_merge_translate_tool = params_dict.get("srt merge translate tool", "google")
        self.srt_merge_translate_key = params_dict.get("srt merge translate key", "")
        self.srt_merge_zh_to_text = params_dict.get("srt merge zh to text", False)
        self.srt_to_voice_source = params_dict.get("srt to voice srouce", False)
        self.TTS = params_dict.get("TTS", "edge")
        self.TTS_param = params_dict.get("TTS param", "")
        self.voice_connect = params_dict.get("voice connect", False)
        self.audio_zh_transcribe = params_dict.get("audio zh transcribe", False)
        self.audio_zh_transcribe_model = params_dict.get("audio zh transcribe model", "medium")
        self.video_zh_preview = params_dict.get("video zh preview", False)

    def __repr__(self):
        return (
            f"<WorkflowParams(proxy={self.proxy}, video_id={self.video_id}, "
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
            with open(path, 'w') as file:
                json.dump(params_dict, file, indent=4)
        except IOError:
            print(f"Error: Failed to write to file '{path}'.")