import logging
import requests
import cohere
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes,
    ConversationHandler
)
from dotenv import load_dotenv
import os
import asyncio

# Load .env variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

co = cohere.Client(COHERE_API_KEY)

logging.basicConfig(level=logging.INFO)

# Conversation stages
SELECT_MAIN, SELECT_STATE, SELECT_COUNT = range(3)

# Track user's choices
user_selection = {}

# --- News Fetching ---
def get_news(query, limit=5):
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    res = requests.get(url).json()
    articles = res.get("articles", [])[:limit]

    news_items = []
    for article in articles:
        headline = article["title"]
        link = article["url"]
        try:
            response = co.chat(
                model='command-r-plus',
                message=f"Summarize this news headline with emotion (happy/sad/serious): {headline}"
            )
            summary = response.text.strip()
            news_items.append(f"📰 {summary}\n🔗 {link}")
        except Exception as e:
            print("❌ Error:", e)
            news_items.append(f"❌ Couldn’t summarize: {headline}")
    return news_items

# --- Start Handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("India 🌏")], [KeyboardButton("World 🌐")]]
    await update.message.reply_text("🌍 Choose your region:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return SELECT_MAIN

# --- Handle Main Selection ---
async def handle_main_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    chat_id = update.effective_chat.id
    if "India" in choice:
        user_selection[chat_id] = "India"
        keyboard = [
            [KeyboardButton("Andhra Pradesh"), KeyboardButton("Tamil Nadu")],
            [KeyboardButton("Karnataka"), KeyboardButton("Telangana")],
            [KeyboardButton("Maharashtra"), KeyboardButton("Kerala")],
            [KeyboardButton("Uttar Pradesh"), KeyboardButton("Delhi")],
            [KeyboardButton("West Bengal"), KeyboardButton("Punjab")]
        ]
        await update.message.reply_text("📍 Choose a state:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return SELECT_STATE
    else:
        user_selection[chat_id] = "World"
        await update.message.reply_text("🌐 How many articles do you want? (e.g., 5)")
        return SELECT_COUNT

# --- Handle State Choice ---
async def handle_state_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = update.message.text
    user_selection[update.effective_chat.id] = state
    await update.message.reply_text(f"📥 How many articles for {state}?")
    return SELECT_COUNT

# --- Handle Article Count ---
async def handle_article_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        count = int(update.message.text)
    except:
        await update.message.reply_text("❗ Please enter a valid number.")
        return SELECT_COUNT

    topic = user_selection.get(chat_id, "India")
    await update.message.reply_text(f"🕵️ Fetching {count} latest news for: {topic}...")
    articles = get_news(topic, count)
    for item in articles:
        await update.message.reply_text(item)
        await asyncio.sleep(0.5)

    return ConversationHandler.END

# --- Cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# --- Main ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_MAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_choice)],
            SELECT_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_state_choice)],
            SELECT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_article_count)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("🤖 Telegram bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
