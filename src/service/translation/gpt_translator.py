import requests
import json
import concurrent.futures
import time
import tenacity
from .translator import Translator

DEFAULT_URL = "https://api.openai.com/v1/"
GHATGPT_TERMS_FILE = "../../../configs/gpt_terms.json"


class GPTTranslator(Translator):
    def __init__(self, api_key, model_name="gpt-3.5-turbo-0125", proxies=None, terms_file=GHATGPT_TERMS_FILE):
        self.api_key = api_key
        self.base_url = DEFAULT_URL
        self.model_name = model_name
        self.proxies = proxies
        self.terms = {}
        self.load_terms(terms_file)

    def load_terms(self, terms_file):
        with open(terms_file, 'r', encoding='utf-8') as f:
            self.terms = json.load(f)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=3, max=6),
                    stop=tenacity.stop_after_attempt(3),
                    reraise=True)
    def request_llm(self, system_text="",
                    assistant_text='',
                    user_text="",
                    max_tokens=1200):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_text,
                },
                {
                    "role": "assistant",
                    "content": assistant_text,
                },
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
            "max_tokens": max_tokens
        }
        response = requests.post(self.base_url + "/chat/completions", headers=headers, json=payload,
                                 proxies=self.proxies)
        return response.json()

    def process_text(self, text, max_tokens):
        st = time.time()
        system_text = ("You are a professional subtitle translator that translates English subtitles to idiomatic "
                       "Chinese subtitles.")
        assistant_text = f"Here are some key terms and their translations:\n{json.dumps(self.terms, ensure_ascii=False)}"
        user_text = f"""You are a professional video subtitle translator.
        You need to translate a segment of subtitles and correct obvious word errors based on the context.
        Additionally, you need to consider some translation rules for terminology provided above.
        Below is the subtitle segment that needs to be translated:\n\n
        ```
        {text}
        ```
        your output format should be:
        ```
        translated text
        ```
        """

        results = self.request_llm(system_text=system_text,
                                   assistant_text=assistant_text,
                                   user_text=user_text,
                                   max_tokens=max_tokens)
        et = time.time()
        text_result = results['choices'][0]['message']['content']
        if '```' in text_result:
            text_result = text_result.split('```')[1]
            text_result = text_result.strip().replace("\n", "").replace("translated text", "").replace("```", "")
        result_dict = {"text_result": text_result,
                       "model": results['model'],
                       "usage": results['usage'],
                       "all_usage": results['usage']['prompt_tokens'] + results['usage']['completion_tokens'] * 3,
                       'time': et - st}
        return result_dict

    def translate_en_to_zh(self, texts, max_tokens=1200, max_workers=30):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_text, text, max_tokens) for text in texts]
            results = [future.result() for future in futures]
        return [result['text_result'] for result in results]
