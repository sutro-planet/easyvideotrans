from src.service.translation.translator import Translator
import srt


class DeepLTranslator(Translator):
    def __init__(self, key):
        self.key = key

    def translate_en_to_zh(self, texts):
        translator = deepl.Translator(self.key)
        textEn = "\n".join(texts)
        textZh = translator.translate_text(textEn, target_lang="zh")
        textsZh = str(textZh).split("\n")
        return textsZh
