import json
import os
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseHandler:
    def __init__(self, knowledge_base_dir: str = "./knowledge_base"):
        self.knowledge_base_dir = knowledge_base_dir
        self.faq_data = self._load_faq()
        self.schedule_data = self._load_schedule()
        self.rules_data = self._load_rules()
        logger.info(f"База знаний загружена: {len(self.faq_data)} FAQ, расписание: {bool(self.schedule_data)}")
    
    def _load_faq(self) -> List[Dict]:
        """Загружает FAQ из JSON файла"""
        faq_path = os.path.join(self.knowledge_base_dir, "faq.json")
        if not os.path.exists(faq_path):
            logger.warning(f"Файл FAQ не найден: {faq_path}")
            return []
        
        try:
            with open(faq_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Преобразуем в плоский список
            faq_list = []
            for category, items in data.items():
                for item in items:
                    item['category'] = category
                    faq_list.append(item)
            
            return faq_list
            
        except Exception as e:
            logger.error(f"Ошибка загрузки FAQ: {e}")
            return []
    
    def _load_schedule(self) -> str:
        """Загружает расписание из Markdown файла"""
        schedule_path = os.path.join(self.knowledge_base_dir, "schedule.md")
        if not os.path.exists(schedule_path):
            return ""
        
        try:
            with open(schedule_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания: {e}")
            return ""
    
    def _load_rules(self) -> str:
        """Загружает правила из Markdown файла"""
        rules_path = os.path.join(self.knowledge_base_dir, "rules.md")
        if not os.path.exists(rules_path):
            return ""
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Ошибка загрузки правил: {e}")
            return ""
    
    def search_faq(self, question: str, max_results: int = 3) -> str:
        """Ищет релевантные FAQ по вопросу"""
        if not self.faq_data:
            return ""
        
        question_lower = question.lower()
        words = set(re.findall(r'\w+', question_lower))
        
        # Считаем релевантность
        scored_items = []
        for item in self.faq_data:
            score = 0
            
            # Проверяем вопрос
            item_question = item.get('question', '').lower()
            item_answer = item.get('answer', '').lower()
            
            for word in words:
                if word in item_question:
                    score += 2
                if word in item_answer:
                    score += 1
            
            if score > 0:
                scored_items.append({
                    'score': score,
                    'question': item.get('question', ''),
                    'answer': item.get('answer', ''),
                    'category': item.get('category', 'general')
                })
        
        # Сортируем по релевантности
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        # Форматируем результат
        if not scored_items:
            return ""
        
        context = "Информация из базы знаний:\n\n"
        for i, item in enumerate(scored_items[:max_results]):
            context += f"{i+1}. **{item['question']}**\n"
            context += f"   Ответ: {item['answer']}\n"
            context += f"   (Категория: {item['category']})\n\n"
        
        return context
    
    def get_schedule_summary(self) -> str:
        """Возвращает краткое расписание"""
        if not self.schedule_data:
            return "Расписание не загружено."
        
        # Извлекаем только основные события
        lines = self.schedule_data.split('\n')
        schedule_lines = []
        for line in lines:
            if any(time_marker in line for time_marker in ['00:', '30:', ' - ', '●', '•', '*']):
                schedule_lines.append(line.strip())
        
        if schedule_lines:
            return "Расписание:\n" + "\n".join(schedule_lines[:10])
        else:
            return self.schedule_data[:500] + "..." if len(self.schedule_data) > 500 else self.schedule_data