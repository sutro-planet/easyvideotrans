from abc import ABC, abstractmethod


class TTSClient(ABC):
    @abstractmethod
    def srt_to_voice(self, srt_file_path, output_dir):
        pass
