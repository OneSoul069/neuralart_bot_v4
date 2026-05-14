"""Psychologist handlers with reply keyboard menu exit."""

import asyncio
import html
import logging
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.states import PsychologistStates
from bot.database import Database
from bot.keyboards import auth_start_kb, main_menu_kb

logger = logging.getLogger(__name__)

router = Router()

def psych_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        is_persistent=True,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напишите сообщение психологу"
    )

def format_telegram_html(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped, flags=re.DOTALL)
    return escaped

def split_text(text: str, max_length: int = 3500) -> list[str]:
    parts = []
    current_part = ""

    for paragraph in text.split("\n\n"):
        if len(paragraph) > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = ""
            for index in range(0, len(paragraph), max_length):
                parts.append(paragraph[index:index + max_length].strip())
            continue

        if len(current_part) + len(paragraph) + 2 > max_length:
            if current_part:
                parts.append(current_part.strip())
            current_part = paragraph + "\n\n"
        else:
            current_part += paragraph + "\n\n"

    if current_part:
        parts.append(current_part.strip())

    return parts or [text]

async def split_and_send(message: Message, text: str):
    parts = split_text(text)
    for i, part in enumerate(parts):
        await message.answer(
            format_telegram_html(part),
            reply_markup=psych_menu_kb(),
            parse_mode="HTML"
        )
        if i < len(parts) - 1:
            await asyncio.sleep(0.3)


@router.callback_query(F.data == "psychologist")
async def start_psychologist(callback: CallbackQuery, state: FSMContext, db: Database, psych_api):
    user = db.get_or_create_user(tg_id=callback.from_user.id)

    if not user["is_verified"]:
        await callback.message.answer(
            "🔐 <b>Требуется регистрация</b>\n\nДля доступа к психологу необходимо зарегистрировать аккаунт.",
            reply_markup=auth_start_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.set_state(PsychologistStates.in_session)

    greeting = (
        "🧠 <b>Сессия с психологом начата</b>\n\n"
        "Я — опытный психолог-консультант. Можешь писать всё, что беспокоит.\n"
        "Я буду слушать и предлагать практики.\n\n"
        "Чтобы завершить сессию и вернуться в меню — нажми кнопку <b>«🏠 Главное меню»</b> внизу."
    )

    await callback.message.answer(
        greeting,
        reply_markup=psych_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PsychologistStates.in_session, F.text.in_({"🏠 Главное меню", "◀️ Назад"}))
async def exit_psychologist(message: Message, state: FSMContext, db: Database):
    await state.clear()

    await message.answer(
        "Сессия с психологом завершена.",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )


@router.message(PsychologistStates.in_session)
async def handle_psych_message(message: Message, state: FSMContext, db: Database, psych_api):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()

    if not user_text:
        await message.answer(
            "Напиши сообщение текстом или нажми «🏠 Главное меню», чтобы завершить сессию.",
            reply_markup=psych_menu_kb()
        )
        return

    db.save_psych_message(user_id, user_text, "user")
    history = db.get_psych_history(user_id, limit=20)

    try:
        if psych_api is None:
            raise Exception("Psychologist API не инициализирован")

        response = await psych_api.chat(history)
        db.save_psych_message(user_id, response, "assistant")

        await split_and_send(message, response)

    except Exception as e:
        logger.error(f"Psychologist API error: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла техническая ошибка. Попробуй написать ещё раз или нажми «🏠 Главное меню».",
            reply_markup=psych_menu_kb()
        )