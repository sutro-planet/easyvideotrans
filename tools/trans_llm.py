import requests
import json
import concurrent.futures
import time
import tenacity

DEFAULT_URL = "https://api.openai.com/v1/"

class TranslatorClass:
    def __init__(self, 
                 api_key, 
                 base_url=DEFAULT_URL,
                 model_name="gpt-3.5-turbo-0125",
                 proxies=None):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.terms = {}
        self.proxies = proxies

    def load_terms(self, terms_file):
        with open(terms_file, 'r', encoding='utf-8') as f:
            self.terms = json.load(f)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=3, max=6),
                    stop=tenacity.stop_after_attempt(3),
                    reraise=True)
    def request_llm(self, system_text="",
                    assistant_text='',
                    user_text="",
                    max_tokens=1200,
                    ):
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
        response = requests.post(self.base_url+"/chat/completions", headers=headers, json=payload, proxies=self.proxies)
        return response.json()
    
    def process_text(self, text, max_tokens):
        st = time.time()
        system_text = "You are a professional subtitle translator that translates English subtitle to idiomatic Chinese subtitle."
        assistant_text = f"Here are some key terms and their translations:\n{json.dumps(self.terms, ensure_ascii=False)}"
        user_text = f"""You are a professional video subtitle translator. You need to translate a segment of subtitles and correct obvious word errors based on the context. Additionally, you need to consider some translation rules for terminology provided above. Below is the subtitle segment that needs to be translated:\n\n
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
                                   max_tokens=max_tokens
                                   )
        et = time.time()
        text_result = results['choices'][0]['message']['content']
        # print("original text_result:", text_result)
        if '```' in text_result:
            text_result = text_result.split('```')[1]
            text_result = text_result.strip().replace("\n", "").replace("translated text", "").replace("```", "")
        # print("text_result:", text_result)
        result_dict = {"text_result": text_result,
                       "model": results['model'],
                       "usage": results['usage'],
                       "all_usage": results['usage']['prompt_tokens']+results['usage']['completion_tokens']*3,
                       'time': et - st,                       
                       }
        return result_dict

    def translate_batch(self, texts, max_tokens, max_workers=30):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_text, text, max_tokens) for text in texts]
            results = [future.result() for future in futures]
        return results


def main():
    # 使用示例
    api_key = 'sk-xxxxx'
    # base_url = "https://xxx/v1"
    proxies = {
        'http': "127.0.0.1:7890",
        'https': "127.0.0.1:7890",
        'socks5': "127.0.0.1:7890"
    }
    
    translator = TranslatorClass(api_key, proxies=proxies)
    
    # 加载术语文件
    terms_file = 'tools/terms.json'
    translator.load_terms(terms_file)
    
    # 单个文本翻译
    text = "This is an example text to be translated."
    max_tokens = 1200
    result = translator.process_text(text, max_tokens)
    print("Translated text:", result['text_result'])
    print("Process time:", result['time'])
    
    # 批量文本翻译
    texts = [
        "This is the first example text to be translated.",
        "This is the second example text to be translated.",
        "This is the third example text to be translated."
    ]
    results = translator.translate_batch(texts, max_tokens)
    for i, result in enumerate(results, 1):
        print(f"Translated text {i}:", result['text_result'])
        print(f"Process time {i}:", result['time'])

if __name__ == '__main__':
    main()
