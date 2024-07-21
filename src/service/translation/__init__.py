from .translator import Translator
from .deepl_translator import DeepLTranslator
from .google_translator import GoogleTranslator
from .gpt_translator import GPTTranslator
from .srt import srt_sentense_merge, srt_to_text

__all__ = [
    "Translator",
    "DeepLTranslator",
    "GoogleTranslator",
    "GPTTranslator",
    "srt_sentense_merge",
    "srt_to_text",
    "get_translator",
]


def get_translator(translate_vendor, api_key=None, proxies=None):
    if translate_vendor == "google":
        return GoogleTranslator(proxy=proxies)
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
