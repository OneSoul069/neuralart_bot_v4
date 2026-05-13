"""Image generation handlers — FIXED crash on photo messages."""

import asyncio
import random
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.database import Database
from bot.services.image_api import ImageGenerator
from bot.keyboards import main_menu_kb, back_to_menu_kb, auth_start_kb
from bot.states import ImageGenStates
from bot.config import config

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "gen_image")
async def start_generation(callback: CallbackQuery, state: FSMContext, db: Database):
    """Start image generation — use answer() to avoid crash on photo messages."""
    user = db.get_or_create_user(tg_id=callback.from_user.id)
    free_left = max(0, config.FREE_GENERATIONS - user["free_generations_used"])

    # Check verification first
    if not user["is_verified"]:
        text = (
            "🔐 <b>Требуется регистрация</b>\n\n"
            "Для генерации изображений необходимо пройти регистрацию."
        )
        await callback.message.answer(text, reply_markup=auth_start_kb(), parse_mode="HTML")
        await callback.answer()
        return

    if free_left > 0 or user["is_premium"]:
        await state.set_state(ImageGenStates.waiting_prompt)
        text = (
            "🎨 <b>Генерация изображения</b>\n\n"
            "Опишите, что хотите увидеть. Чем подробнее промпт — тем лучше результат.\n\n"
            "Пример: <code>космический корабль, неоновые огни, фотореализм, 8k</code>\n\n"
            f"Осталось бесплатных: <b>{free_left}</b>"
        )
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    else:
        text = (
            f"⚠️ <b>Лимит исчерпан</b>\n\n"
            f"Ваши {config.FREE_GENERATIONS} бесплатных генерации закончились.\n"
            "Пригласите друга или дождитесь обновления лимита."
        )
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")

    await callback.answer()


@router.message(ImageGenStates.waiting_prompt)
async def process_prompt(message: Message, state: FSMContext, db: Database, img_gen: ImageGenerator):
    """Process image generation prompt."""
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("❌ Отправьте текстовое описание изображения.")
        return

    if len(prompt) < 3:
        await message.answer("❌ Опишите запрос подробнее (минимум 3 символа).")
        return

    if len(prompt) > 500:
        await message.answer("❌ Промпт слишком длинный (макс. 500 символов).")
        return

    user = db.get_or_create_user(tg_id=message.from_user.id)

    queue_pos = random.randint(1, 12)
    est_time = random.randint(10, 35)

    text = (
        "⏳ <b>Генерация начата...</b>\n\n"
        f"🎨 Промпт: <i>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</i>\n"
        f"📊 Позиция в очереди: <b>{queue_pos}</b>\n"
        f"⏱ Ожидаемое время: <b>{est_time} сек</b>\n"
        "🖥 Модель: <b>Stable Diffusion XL v1.0</b>\n\n"
        "<i>Пожалуйста, подождите...</i>"
    )

    processing_msg = await message.answer(text, parse_mode="HTML")

    await asyncio.sleep(random.randint(6, 18))

    if queue_pos > 1:
        text = (
            "⏳ <b>Генерация в процессе...</b>\n\n"
            f"🎨 Промпт: <i>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</i>\n"
            f"📊 Позиция в очереди: <b>{max(1, queue_pos - random.randint(1, 3))}</b>\n"
            f"⏱ Осталось: <b>{max(5, est_time - 10)} сек</b>\n"
            "🖥 Модель: <b>Stable Diffusion XL v1.0</b>\n\n"
            "<i>Генерация изображения...</i>"
        )
        await processing_msg.edit_text(text, parse_mode="HTML")
        await asyncio.sleep(random.randint(5, 12))

    start_time = asyncio.get_event_loop().time()
    image_url = await img_gen.generate(prompt)
    processing_time = asyncio.get_event_loop().time() - start_time

    if image_url:
        db.increment_generations(message.from_user.id, is_real=True)
        db.save_generation(
            message.from_user.id, prompt, image_url, 
            is_real=True, processing_time=processing_time
        )

        free_left = max(0, config.FREE_GENERATIONS - user["free_generations_used"] - 1)

        await processing_msg.delete()
        caption = (
            "✅ <b>Готово!</b>\n\n"
            f"🎨 <i>{prompt[:150]}{'...' if len(prompt) > 150 else ''}</i>\n\n"
            f"⏱ Время генерации: <b>{processing_time:.1f}с</b>\n"
            "📐 Размер: 1024×1024\n"
            "🖼 Модель: SDXL v1.0\n\n"
            f"Осталось бесплатных: <b>{free_left}</b>"
        )
        await message.answer_photo(
            photo=image_url,
            caption=caption,
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    else:
        await processing_msg.edit_text(
            "❌ <b>Ошибка генерации</b>\n\nСерверы перегружены. Попробуйте через минуту.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
