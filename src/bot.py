import anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.agent import run_agent
from src.config import settings
from src.db import get_collection

USAGE_HINT = (
    "Usage: /acc <your request>\n\n"
    "Examples:\n"
    "• /acc Заряди 100$ за оновлення блоків\n"
    "• /acc Які є незавершені задачі?\n"
    "• /acc Mark payment as done for documentation task"
)


async def accounter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(USAGE_HINT)
        return

    user_prompt = " ".join(context.args)
    chat_id = update.effective_chat.id

    await update.effective_chat.send_action("typing")

    collection = get_collection(settings.mongodb_uri, settings.mongodb_db_name)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await run_agent(
            client=client,
            collection=collection,
            chat_id=chat_id,
            user_prompt=user_prompt,
        )
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def create_bot() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("acc", accounter_handler))
    return app
