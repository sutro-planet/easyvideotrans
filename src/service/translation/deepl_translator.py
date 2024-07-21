import deepl
from src.service.translation.translator import Translator


class DeepLTranslator(Translator):
    def __init__(self, key):
        self.key = key

    def translate_en_to_zh(self, texts):
        dl_translator = deepl.Translator(self.key)
        textEn = "\n".join(texts)
        textZh = dl_translator.translate_text(textEn, target_lang="zh")
        textsZh = str(textZh).split("\n")
        return textsZh
