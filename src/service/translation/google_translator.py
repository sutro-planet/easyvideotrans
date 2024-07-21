from .translator import Translator
from pygtrans import Translate


class GoogleTranslator(Translator):
    def __init__(self, proxy=""):
        self.proxy = proxy
        if proxy == "":
            self.client = Translate()
        else:
            self.client = Translate(proxies={'https': self.proxy})

    def translate_en_to_zh(self, texts):
        texts_response = self.client.translate(texts, target='zh')
        texts_translated = [txtResponse.translatedText for txtResponse in texts_response]
        return texts_translated
