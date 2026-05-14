"""Personality and love language assessments."""

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.keyboards import auth_start_kb, back_to_menu_kb, main_menu_kb
from bot.states import AssessmentStates
from bot.handlers.psychologist import format_telegram_html, safe_delete, split_text

logger = logging.getLogger(__name__)

router = Router()


@dataclass(frozen=True)
class Assessment:
    key: str
    title: str
    description: str
    questions: tuple[str, ...]


ASSESSMENTS = {
    "archetype": Assessment(
        key="archetype",
        title="🧩 Архетип личности",
        description="Определяет ведущий психологический архетип по стилю решений, мотивации и отношениям.",
        questions=(
            "Что чаще всего движет тобой: свобода, безопасность, признание, любовь, влияние, знания или творчество?",
            "Когда появляется сложная проблема, ты скорее действуешь сразу, анализируешь, просишь поддержки или ждёшь подходящего момента?",
            "Какая роль в компании тебе ближе: лидер, советчик, исследователь, миротворец, вдохновитель, защитник или бунтарь?",
            "Чего ты больше боишься: потерять контроль, быть отвергнутым, ошибиться, стать обычным, зависеть от других или не реализоваться?",
            "Что люди чаще всего получают рядом с тобой: спокойствие, драйв, ясность, заботу, идеи, уверенность или честную встряску?",
            "Какая фраза ближе: «я справлюсь», «я пойму», «я защищу», «я создам», «я докажу», «я помогу»?",
            "Что тебе труднее всего: просить помощи, долго ждать, доверять, принимать критику, отдыхать или выбирать одно направление?",
        ),
    ),
    "love_language": Assessment(
        key="love_language",
        title="💞 Язык любви",
        description="Определяет, через что человек сильнее всего чувствует любовь и близость.",
        questions=(
            "Что сильнее всего даёт тебе чувство, что тебя любят: слова, помощь, время вместе, подарки или прикосновения?",
            "Что больнее всего: холодные слова, отсутствие внимания, когда не помогают, забытые важные даты или нехватка физической близости?",
            "Как ты сам чаще всего показываешь любовь человеку?",
            "Представь тяжёлый день. Что от близкого человека помогло бы тебе быстрее всего восстановиться?",
            "Что для тебя ценнее: длинный разговор, объятие, сделанное за тебя дело, искренний комплимент или маленький продуманный подарок?",
            "Из-за чего в отношениях у тебя чаще появляется ощущение «меня не ценят»?",
            "Какой идеальный знак внимания ты бы хотел получать регулярно?",
        ),
    ),
}


def get_assessment(kind: str) -> Assessment:
    return ASSESSMENTS[kind]


async def send_question(message: Message, state: FSMContext):
    data = await state.get_data()
    assessment = get_assessment(data["assessment_kind"])
    question_index = data["question_index"]
    question = assessment.questions[question_index]
    text = (
        f"<b>{assessment.title}</b>\n\n"
        f"Вопрос {question_index + 1}/{len(assessment.questions)}:\n"
        f"{question}"
    )
    await message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data.in_({"archetype_test", "love_language_test"}))
async def start_assessment(callback: CallbackQuery, state: FSMContext, db: Database):
    user = db.get_or_create_user(tg_id=callback.from_user.id)
    if not user["is_verified"]:
        await callback.message.answer(
            "🔐 <b>Требуется регистрация</b>\n\nДля прохождения теста необходимо зарегистрировать аккаунт.",
            reply_markup=auth_start_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    kind = "archetype" if callback.data == "archetype_test" else "love_language"
    assessment = get_assessment(kind)
    await state.set_state(AssessmentStates.answering)
    await state.update_data(
        assessment_kind=kind,
        question_index=0,
        answers=[],
    )

    intro = (
        f"<b>{assessment.title}</b>\n\n"
        f"{assessment.description}\n\n"
        "Ответь на несколько вопросов своими словами. В конце я соберу результат через DeepSeek."
    )
    await callback.message.answer(intro, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await send_question(callback.message, state)
    await callback.answer()


@router.message(AssessmentStates.answering)
async def process_assessment_answer(message: Message, state: FSMContext, db: Database, assessment_api):
    answer = (message.text or "").strip()
    if not answer:
        await message.answer("Ответь текстом, пожалуйста.", reply_markup=back_to_menu_kb())
        return

    data = await state.get_data()
    assessment = get_assessment(data["assessment_kind"])
    question_index = data["question_index"]
    answers = data["answers"]
    answers.append({
        "question": assessment.questions[question_index],
        "answer": answer,
    })

    question_index += 1
    if question_index < len(assessment.questions):
        await state.update_data(question_index=question_index, answers=answers)
        await send_question(message, state)
        return

    await state.clear()
    status_msg = await message.answer("🔎 Анализирую ответы через DeepSeek...")

    try:
        result = await assessment_api.analyze(assessment.title, assessment.description, answers)
        await safe_delete(status_msg)
        parts = split_text(result)
        for index, part in enumerate(parts):
            await message.answer(
                format_telegram_html(part),
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
            if index < len(parts) - 1:
                await asyncio.sleep(0.3)
    except Exception as exc:
        await safe_delete(status_msg)
        logger.error(f"Assessment API error: {exc}", exc_info=True)
        await message.answer(
            "⚠️ Не удалось получить результат. Попробуй пройти тест ещё раз позже.",
            reply_markup=main_menu_kb()
        )
