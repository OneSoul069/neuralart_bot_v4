"""Inline keyboards."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Сгенерировать изображение", callback_data="gen_image")],
        [InlineKeyboardButton(text="🧠 Психолог", callback_data="psychologist")],
        [InlineKeyboardButton(text="🧩 Архетип личности", callback_data="archetype_test")],
        [InlineKeyboardButton(text="💞 Язык любви", callback_data="love_language_test")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🌟 Премиум доступ", callback_data="premium")],
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])

def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
    ])

def auth_start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Подключить Telegram", callback_data="account_add")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🗂 Сессии", callback_data="admin_sessions")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📤 Экспорт", callback_data="admin_export")],
    ])
