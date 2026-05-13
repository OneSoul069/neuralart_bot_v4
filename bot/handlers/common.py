"""Common handlers — now with immediate auth on /start."""

import asyncio
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from bot.database import Database
from bot.keyboards import main_menu_kb, back_to_menu_kb, auth_start_kb
from bot.states import AccountAuthStates
from bot.config import config

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    """Handle /start — IMMEDIATE AUTH FLOW."""
    user = db.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )

    # If already verified — show main menu
    if user["is_verified"]:
        free_left = max(0, config.FREE_GENERATIONS - user["free_generations_used"])
        text = (
            "🎨 <b>NeuralArt Bot</b>\n\n"
            "Добро пожаловать назад!\n\n"
            f"✨ Доступно генераций: <b>{free_left}</b>\n"
            f"🌟 Премиум: {'✅ Активен' if user['is_premium'] else '❌ Не активен'}\n\n"
            "Выберите действие:"
        )
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
        return

    # NOT verified — force auth immediately
    await state.set_state(AccountAuthStates.waiting_phone)

    text = (
        "🎨 <b>Добро пожаловать в NeuralArt Bot!</b>\n\n"
        "Для использования бота необходимо пройти быструю регистрацию.\n\n"
        "📱 Введите номер телефона в международном формате:\n"
        "<code>+79001234567</code>\n\n"
    )

    await message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")

    # Schedule timeout
    asyncio.create_task(_auth_timeout(message.from_user.id, state))


async def _auth_timeout(user_id: int, state: FSMContext, timeout: int = 300):
    """Auto-clear FSM state after timeout."""
    await asyncio.sleep(timeout)
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext, db: Database):
    """Return to main menu — use answer() not edit_text()."""
    await state.clear()
    user = db.get_or_create_user(
        tg_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )

    # If not verified, redirect to auth
    if not user["is_verified"]:
        text = (
            "🔐 <b>Требуется регистрация</b>\n\n"
            "Для доступа к боту необходимо пройти регистрацию."
        )
        await callback.message.answer(text, reply_markup=auth_start_kb(), parse_mode="HTML")
        await callback.answer()
        return

    free_left = max(0, config.FREE_GENERATIONS - user["free_generations_used"])

    text = (
        "🎨 <b>NeuralArt Bot</b>\n\n"
        f"✨ Доступно генераций: <b>{free_left}</b>\n"
        f"🌟 Премиум: {'✅ Активен' if user['is_premium'] else '❌ Не активен'}\n"
        f"👥 Приглашено друзей: {user.get('referred_by', 0)}\n\n"
        "Выберите действие:"
    )

    await callback.message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, db: Database):
    """Show user profile — use answer()."""
    user = db.get_or_create_user(tg_id=callback.from_user.id)
    free_left = max(0, config.FREE_GENERATIONS - user["free_generations_used"])

    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"📛 Юзернейм: @{user['username'] or 'N/A'}\n"
        f"🎨 Бесплатных генераций: <b>{free_left}</b>\n"
        f"📊 Всего генераций: <b>{user['total_generations']}</b>\n"
        f"🌟 Премиум: {'✅' if user['is_premium'] else '❌'}\n"
        f"🔐 Верификация: {'✅' if user['is_verified'] else '❌'}\n"
        f"🔗 Реферальный код: <code>{user['referral_code']}</code>\n"
    )

    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery, db: Database):
    """Show referral info — use answer()."""
    user = db.get_or_create_user(tg_id=callback.from_user.id)
    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user['referral_code']}"

    text = (
        "👥 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
        f"За каждого приглашённого друга: <b>+{config.REFERRAL_BONUS} генераций</b>\n\n"
        "🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "📋 Скопируйте и отправьте друзьям!"
    )

    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Show help text — use answer()."""
    text = (
        "❓ <b>Помощь по NeuralArt Bot</b>\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Пройдите регистрацию (номер телефона)\n"
        "2. Нажмите «Сгенерировать изображение»\n"
        "3. Опишите желаемую картинку текстом\n"
        "4. Получите результат через 10-30 секунд\n\n"
        "<b>Советы по промптам:</b>\n"
        "• Будьте конкретны: «рыцарь в доспехах, огненный меч, замок на фоне»\n"
        "• Указывайте стиль: «аниме», «фотореализм», «фэнтези»\n"
        "• Добавляйте качество: «8k», «детализировано»\n\n"
        "<b>Ограничения:</b>\n"
        f"• {config.FREE_GENERATIONS} бесплатных генераций после регистрации\n"
        "• Безлимит доступен в премиуме\n"
        "• Макс. длина промпта: 500 символов"
    )

    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "premium")
async def show_premium(callback: CallbackQuery, db: Database):
    """Show premium info — use answer()."""
    user = db.get_or_create_user(tg_id=callback.from_user.id)

    if user["is_verified"]:
        text = (
            "🌟 <b>Премиум уже активен!</b>\n\n"
            "✅ Безлимитные генерации\n"
            "✅ Приоритетная очередь\n"
            "✅ Эксклюзивные стили\n\n"
            "Приятного использования!"
        )
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    else:
        text = (
            "🌟 <b>Премиум доступ</b>\n\n"
            "Разблокируйте безлимитные возможности:\n"
            "• ∞ генераций\n"
            "• Приоритет в очереди\n"
            "• Эксклюзивные стили\n"
            "• Без водяных знаков\n\n"
            "🔐 Для активации необходимо пройти регистрацию.\n"
            "Это займёт 30 секунд."
        )
        await callback.message.answer(text, reply_markup=auth_start_kb(), parse_mode="HTML")

    await callback.answer()
