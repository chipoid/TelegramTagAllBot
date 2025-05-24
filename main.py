import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# === Конфигурация ===
TOKEN = os.getenv("BOT_TOKEN", "ТОКЕН_ТВОЕГО_БОТА")
DB_FILE = "users.json"
ACTIVE_DAYS = 7
FLOOD_TIMEOUT = 60  # 1 минута между вызовами /all в группе

# Хранилище времени последнего вызова команды по чатам
last_call = {}

# === Работа с базой пользователей ===
def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === Трекинг сообщений ===
async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not user or user.is_bot or not chat:
        return

    users = load_users()
    chat_id = str(chat.id)
    if chat_id not in users:
        users[chat_id] = {}

    users[chat_id][str(user.id)] = {
        "username": user.username,
        "first_name": user.first_name,
        "last_seen": datetime.utcnow().isoformat()
    }

    save_users(users)

# === Команда /all ===
async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    now = datetime.utcnow()
    chat_id = str(chat.id)

    # Антифлуд
    if chat_id in last_call:
        delta = (now - last_call[chat_id]).total_seconds()
        if delta < FLOOD_TIMEOUT:
            await context.bot.send_message(chat.id, "⏳ Подождите немного перед следующим вызовом.")
            return
    last_call[chat_id] = now

    users = load_users()
    if chat_id not in users:
        await context.bot.send_message(chat.id, "❌ Нет активных пользователей.")
        return

    mentions = []
    for user_data in users[chat_id].values():
        try:
            seen_time = datetime.fromisoformat(user_data["last_seen"])
            if (now - seen_time).days > ACTIVE_DAYS:
                continue

            if user_data.get("username"):
                mentions.append(f"@{user_data['username']}")
            else:
                mentions.append(user_data.get("first_name", "пользователь"))
        except:
            continue

    if not mentions:
        await context.bot.send_message(chat.id, "❌ Нет активных участников за последние 7 дней.")
        return

    text = "🔔 Внимание: " + ", ".join(mentions)

    if len(text) > 4096:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await context.bot.send_message(chat.id, part)
    else:
        await context.bot.send_message(chat.id, text)

# === Запуск приложения ===
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track_activity))
    app.add_handler(CommandHandler("all", all_command))

    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()