import os
import json
import asyncio
import logging
from datetime import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ---------- ЛОГИ ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- ТОКЕН ----------

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден! Установи переменную окружения.")

DATA_FILE = "users.json"

# ---------- Загрузка / сохранение данных ----------

def load_users():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения {DATA_FILE}: {e}")
    return {}

def save_users(users):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения {DATA_FILE}: {e}")

users = load_users()

# ---------- Юбилейные дни ----------

ANNIVERSARY_DAYS = {
    10: "💖 10 дней вместе — это только начало конца!",
    20: "🔥 20 дней в отношениях! Ты точно уверен?",
    50: "🔥 50 дней вместе! Это уже серьёзно",
    100: "🎉 100 дней вместе! Она точно та самая?",
    150: "🎉 150 дней вместе! Может пора остановиться?"
}

# ---------- /start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ Я нахожусь в отношениях", callback_data="start_relation")]
    ])

    await update.message.reply_text(
        "Привет! 👋\n"
        "Я бот, который считает дни ваших отношений 💖\n\n"
        "Нажми кнопку ниже, если ты сейчас в отношениях:",
        reply_markup=keyboard
    )

# ---------- Начало отношений ----------

async def start_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)

    if chat_id in users and users[chat_id]["active"]:
        await query.answer("Отсчёт уже идёт 🙂", show_alert=True)
        return

    users[chat_id] = {
        "day": 1,
        "active": True
    }
    save_users(users)

    logger.info(f"Отношения начаты: chat_id={chat_id}")

    await query.answer()
    await send_day_message(context, chat_id)

# ---------- Отправка сообщения ----------

async def send_day_message(context, chat_id):
    if chat_id not in users or not users[chat_id]["active"]:
        return

    day = users[chat_id]["day"]
    text = f"День {day}: Ещё не расстались"

    if day in ANNIVERSARY_DAYS:
        text += f"\n\n{ANNIVERSARY_DAYS[day]}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💔 Расстались", callback_data="breakup")]
    ])

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения ({chat_id}): {e}")

# ---------- Подтверждение расставания ----------

async def breakup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data="breakup_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="breakup_no")
        ]
    ])

    await query.answer()
    await query.edit_message_text(
        "Вы точно расстались?",
        reply_markup=keyboard
    )

async def breakup_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)

    users[chat_id]["active"] = False
    save_users(users)

    logger.info(f"Отношения завершены: chat_id={chat_id}")

    await query.answer()
    await query.edit_message_text(
        "💔 Счётчик остановлен.\nСпасибо, что пользовались ботом."
    )

async def breakup_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "💖 Хорошо, продолжаем считать дни!"
    )

# ---------- Ежедневная задача ----------

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Запуск ежедневной задачи")

    for chat_id in users:
        if users[chat_id]["active"]:
            users[chat_id]["day"] += 1
            await send_day_message(context, chat_id)

    save_users(users)

# ---------- main ----------

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_relation, pattern="start_relation"))
    app.add_handler(CallbackQueryHandler(breakup_confirm, pattern="breakup"))
    app.add_handler(CallbackQueryHandler(breakup_yes, pattern="breakup_yes"))
    app.add_handler(CallbackQueryHandler(breakup_no, pattern="breakup_no"))

    app.job_queue.run_daily(
        daily_job,
        time=time(hour=9, minute=0)  # 12:00 МСК
    )

    logger.info("🤖 Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
