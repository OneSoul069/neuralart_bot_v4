import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

# ====================== НАСТРОЙКИ ======================
API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL = "deepseek-chat"          # Можно поменять на "deepseek-reasoner"
# =======================================================

async def test_deepseek():
    if not API_KEY:
        print("❌ Ошибка: Ключ DEEPSEEK_API_KEY не найден в файле .env")
        return

    print(f"🔑 Ключ: {API_KEY[:10]}...{API_KEY[-6:]}")
    print(f"🤖 Модель: {MODEL}\n")

    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Ты — опытный психолог-консультант. Отвечай коротко и по делу."
            },
            {
                "role": "user",
                "content": "Привет! У меня проблемы с мотивацией. Что посоветуешь?"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                print(f"Статус ответа: {resp.status}")

                if resp.status == 200:
                    data = await resp.json()
                    answer = data["choices"][0]["message"]["content"]
                    print("\n✅ УСПЕХ! Ответ от DeepSeek:\n")
                    print(answer)
                else:
                    error = await resp.text()
                    print(f"\n❌ ОШИБКА от DeepSeek:\n{error}")

    except Exception as e:
        print(f"\n❌ Ошибка соединения: {e}")


if __name__ == "__main__":
    asyncio.run(test_deepseek())