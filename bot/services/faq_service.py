import json
from pathlib import Path
from typing import Dict, List

class FAQService:
    def __init__(self):
        self.faq_path = Path(__file__).parent.parent / "models" / "knowledge_base" / "faq.json"
        self.faq_data = self._load_faq_data()
    
    def _load_faq_data(self) -> Dict:
        """Загружает данные из faq.json"""
        try:
            with open(self.faq_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"⚠️ Файл {self.faq_path} не найден!")
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка чтения JSON: {e}")
            return {}
    
    def get_categories(self) -> List[str]:
        """Возвращает список категорий"""
        return list(self.faq_data.keys())
    
    def get_questions_by_category(self, category: str) -> List[Dict]:
        """Возвращает вопросы по категории"""
        return self.faq_data.get(category, [])
    
    def get_all_questions(self) -> List[Dict]:
        """Возвращает все вопросы с уникальными ID"""
        all_questions = []
        for category, questions in self.faq_data.items():
            for i, qa in enumerate(questions):
                all_questions.append({
                    "id": f"{category}_{i}",
                    "category": category,
                    "question": qa["question"],
                    "answer": qa["answer"]
                })
        return all_questions
    
    def search_questions(self, keyword: str) -> List[Dict]:
        """Поиск вопросов по ключевому слову"""
        results = []
        all_questions = self.get_all_questions()
        keyword_lower = keyword.lower()
        
        for q in all_questions:
            if (keyword_lower in q["question"].lower() or 
                keyword_lower in q["answer"].lower()):
                results.append(q)
        return results

faq_service = FAQService()