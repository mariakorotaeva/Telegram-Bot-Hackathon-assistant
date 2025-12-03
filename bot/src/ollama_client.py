# Файл: ollama_client.py
import ollama
import json

class OllamaClient:
    def __init__(self, host="localhost", port=11434):
        self.base_url = f"http://{host}:{port}"
        self.client = ollama.Client(host=f"{host}:{port}")
    
    def list_models(self):
        """Показать все доступные модели"""
        return self.client.list()
    
    def generate_response(self, model_name, prompt, system_prompt=None, **options):
        """Генерация ответа"""
        response = self.client.generate(
            model=model_name,
            prompt=prompt,
            system=system_prompt,
            options={
                'temperature': options.get('temperature', 0.7),
                'num_predict': options.get('max_tokens', 512),
                'top_p': options.get('top_p', 0.9),
                'top_k': options.get('top_k', 40)
            }
        )
        return response['response']
    
    def chat_completion(self, model_name, messages, **options):
        """Чат-комплетирование с историей"""
        response = self.client.chat(
            model=model_name,
            messages=messages,
            options={
                'temperature': options.get('temperature', 0.7),
                'num_predict': options.get('max_tokens', 512)
            }
        )
        return response['message']['content']
    
    def stream_response(self, model_name, prompt, callback):
        """Стриминг ответа"""
        stream = self.client.generate(
            model=model_name,
            prompt=prompt,
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if 'response' in chunk:
                token = chunk['response']
                full_response += token
                callback(token)  # Колбек для обработки каждого токена
        
        return full_response

# Использование
if __name__ == "__main__":
    client = OllamaClient()
    
    # Проверяем модели
    print("Доступные модели:")
    for model in client.list_models()['models']:
        print(f"  - {model['name']}")
    
    # Генерация ответа
    response = client.generate_response(
        model_name="my-ai-assistant",
        prompt="Как мигрировать с монолита на микросервисы?",
        temperature=0.8,
        max_tokens=1024
    )
    
    print("\nОтвет модели:")
    print(response)