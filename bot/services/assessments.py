"""DeepSeek-powered personality assessments."""

import aiohttp
from typing import List, Dict


class AssessmentAPI:
    def __init__(self, api_key: str, model: str = "deepseek-reasoner"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"

    async def analyze(self, title: str, description: str, answers: List[Dict[str, str]]) -> str:
        answers_text = "\n".join(
            f"{index}. Вопрос: {item['question']}\nОтвет: {item['answer']}"
            for index, item in enumerate(answers, 1)
        )
        system_prompt = (
            "Ты — спокойный психологический консультант. "
            "Сделай мягкую развлекательную интерпретацию теста, не ставь диагнозы. "
            "Пиши по-русски, структурно, без Markdown-разметки вроде **жирный**."
        )
        user_prompt = (
            f"Тест: {title}\n"
            f"Описание: {description}\n\n"
            f"Ответы пользователя:\n{answers_text}\n\n"
            "Сформируй результат:\n"
            "1. Главный тип/архетип или язык любви.\n"
            "2. 2–3 вторичных признака.\n"
            "3. Что это значит в отношениях и общении.\n"
            "4. 3 практичных совета.\n"
            "5. Короткое предупреждение, что это не диагноз, а ориентир для саморефлексии."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1200,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

                error_text = await resp.text()
                raise Exception(f"API error {resp.status}: {error_text}")
