"""Psychologist handlers with reply keyboard 'Back'."""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.states import PsychologistStates
from bot.database import Database
from bot.keyboards import main_menu_kb

import logging
logger = logging.getLogger(__name__)

router = Router()

# Reply-клавиатура с кнопкой "Назад"
def psych_back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def split_and_send(message: Message, text: str, parse_mode: str = "HTML"):
    """Разбивает длинный текст на несколько сообщений"""
    max_length = 4000
    if len(text) <= max_length:
        await message.answer(text, parse_mode=parse_mode)
        return

    # Разбиваем по абзацам
    parts = []
    current_part = ""
    
    for paragraph in text.split("\n\n"):
        if len(current_part) + len(paragraph) + 2 > max_length:
            if current_part:
                parts.append(current_part.strip())
            current_part = paragraph + "\n\n"
        else:
            current_part += paragraph + "\n\n"
    
    if current_part:
        parts.append(current_part.strip())

    for i, part in enumerate(parts):
        await message.answer(part, parse_mode=parse_mode)
        if i < len(parts) - 1:
            await asyncio.sleep(0.3)  # небольшая задержка между сообщениями


@router.callback_query(F.data == "psychologist")
async def start_psychologist(callback: Message, state: FSMContext, db: Database, psych_api):
    user_id = callback.from_user.id
    
    await state.set_state(PsychologistStates.in_session)
    
    greeting = (
        "🧠 <b>Сессия с психологом начата</b>\n\n"
        "Я — опытный психолог-консультант. Можешь писать всё, что беспокоит.\n"
        "Я буду слушать и предлагать практики.\n\n"
        "Чтобы вернуться в главное меню — нажми кнопку <b>«◀️ Назад»</b> внизу."
    )
    
    await callback.message.answer(
        greeting, 
        reply_markup=psych_back_kb(), 
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PsychologistStates.in_session, F.text == "◀️ Назад")
async def exit_psychologist(message: Message, state: FSMContext, db: Database):
    await state.clear()
    
    # Убираем reply-клавиатуру и показываем главное меню
    await message.answer(
        "Сессия с психологом завершена.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Показываем главное меню (inline-кнопки)
    from bot.keyboards import main_menu_kb
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )


@router.message(PsychologistStates.in_session)
async def handle_psych_message(message: Message, state: FSMContext, db: Database, psych_api):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()

    if not user_text or user_text == "◀️ Назад":
        return

    db.save_psych_message(user_id, user_text, "user")
    history = db.get_psych_history(user_id, limit=20)

    try:
        if psych_api is None:
            raise Exception("Psychologist API не инициализирован")

        response = await psych_api.chat(history)
        db.save_psych_message(user_id, response, "assistant")

        # Отправляем ответ (с разделением, если длинный)
        await split_and_send(message, response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Psychologist API error: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла техническая ошибка. Попробуй написать ещё раз или нажми «◀️ Назад».",
            reply_markup=psych_back_kb()
        )