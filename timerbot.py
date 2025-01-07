import logging
import os
import time
import threading
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

# Загружаем переменные окружения из .env файла
load_dotenv()

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с кнопками выбора даты для таймера."""
    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data='0')],
        [InlineKeyboardButton("Завтра", callback_data='1')],
        [InlineKeyboardButton("Через 3 дня", callback_data='3')],
        [InlineKeyboardButton("Выбрать дату", callback_data='choose_date')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Выберите дату для таймера:',
        reply_markup=reply_markup
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок для установки таймера."""
    query = update.callback_query
    await query.answer()

    if query.data == 'choose_date':
        await query.message.reply_text(
            "Пожалуйста, введите дату в формате ГГГГ-ММ-ДД:"
        )
        return

    days_to_add = int(query.data)
    target_date = datetime.now() + timedelta(days=days_to_add)
    await set_timer(target_date, query)


async def set_timer(target_date, query):
    """
    Устанавливает таймер на указанную дату и запускает его в отдельном потоке.
    """
    chat_id = query.message.chat_id
    event_time = int((target_date - datetime.now()).total_seconds())

    message = await query.message.reply_text(
        f"Таймер установлен на {target_date.strftime('%Y-%m-%d')}."
    )

    threading.Thread(
        target=run_timer,
        args=(event_time, chat_id, message.message_id)
    ).start()


def run_timer(event_time, chat_id, message_id):
    """Запускает таймер и отправляет сообщение по его истечении."""
    time.sleep(event_time)
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="Таймер завершен! Время события истекло!"
    )


async def handle_date_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Обрабатывает ввод даты пользователем и устанавливает таймер."""
    user_input = update.message.text
    try:
        target_date = datetime.strptime(user_input, '%Y-%m-%d')
        event_time = int((target_date - datetime.now()).total_seconds())

        if event_time < 0:
            await update.message.reply_text(
                "Выберите дату в будущем."
            )
            return

        message = await update.message.reply_text(
            f"Таймер установлен на {target_date.strftime('%Y-%m-%d')}."
        )

        threading.Thread(
            target=run_timer,
            args=(event_time, update.message.chat_id, message.message_id)
        ).start()
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат "
            "ГГГГ-ММ-ДД."
        )


def main():
    """Основная функция для запуска бота."""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("set_date", handle_date_input))

    application.run_polling()


if __name__ == '__main__':
    main()
