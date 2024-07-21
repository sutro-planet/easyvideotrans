from abc import ABC, abstractmethod
import srt
from src.service.translation.deepl_translator import DeepLTranslator
from src.service.translation.google_translator import GoogleTranslator
from src.service.translation.gpt_translator import GPTTranslator


class Translator(ABC):
    @abstractmethod
    def translate_en_to_zh(self, texts: list) -> list:
        pass

    def translate_srt(self, source_file_name_and_path, output_file_name_and_path):
        srt_content = open(source_file_name_and_path, "r", encoding="utf-8").read()
        sub_generator = srt.parse(srt_content)
        sub_title_list = list(sub_generator)
        content_list = [subTitle.content for subTitle in sub_title_list]

        content_list = self.translate_en_to_zh(content_list)
        for i in range(len(sub_title_list)):
            sub_title_list[i].content = content_list[i]

        srt_content = srt.compose(sub_title_list)
        with open(output_file_name_and_path, "w", encoding="utf-8") as file:
            file.write(srt_content)

        return True


def get_translator(translate_vendor, api_key=None, proxies=None):
    if translate_vendor == "google":
        return GoogleTranslator(proxy="")
    elif translate_vendor == "deepl":
        if not api_key:
            raise ValueError("Missing translate key for DeepL.")
        return DeepLTranslator(key=api_key)
    elif "gpt" in translate_vendor:
        if not api_key:
            raise ValueError("Missing translate key for GPT.")
        return GPTTranslator(api_key=api_key, model_name=translate_vendor, proxies=proxies)
    else:
        raise ValueError("Unknown translation vendor.")