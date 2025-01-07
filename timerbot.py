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

# Глобальная переменная для хранения текущей даты
current_date = datetime.now()

def generate_calendar_buttons(year, month):
    """Генерирует кнопки для выбора даты в виде календаря."""
    keyboard = []
    month_start = datetime(year, month, 1)
    # Получаем последний день месяца
    next_month = month + 1 if month < 12 else 1
    year_end = year if month < 12 else year + 1
    month_end = (datetime(year_end, next_month, 1) - timedelta(days=1)).day

    # Добавляем заголовок с днями недели
    keyboard.append([InlineKeyboardButton("Пн", callback_data='ignore'),
                     InlineKeyboardButton("Вт", callback_data='ignore'),
                     InlineKeyboardButton("Ср", callback_data='ignore'),
                     InlineKeyboardButton("Чт", callback_data='ignore'),
                     InlineKeyboardButton("Пт", callback_data='ignore'),
                     InlineKeyboardButton("Сб", callback_data='ignore'),
                     InlineKeyboardButton("Вс", callback_data='ignore')])

    # Заполняем кнопки датами
    day = 1
    while day <= month_end:
        row = []
        for _ in range(7):  # 7 дней в неделе
            if day <= month_end:
                row.append(InlineKeyboardButton(day, callback_data=f'{year}-{month:02d}-{day:02d}'))
            else:
                row.append(InlineKeyboardButton(" ", callback_data='ignore'))
            day += 1
        keyboard.append(row)

    # Добавляем кнопки для навигации по месяцам
    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f'prev_month-{year}-{month}'),
        InlineKeyboardButton(f"{month:02d}/{year}", callback_data='ignore'),
        InlineKeyboardButton(">>", callback_data=f'next_month-{year}-{month}')
    ])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data='back')])
    return keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с кнопками выбора даты для таймера."""
    global current_date
    keyboard = generate_calendar_buttons(current_date.year, current_date.month)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Добро пожаловать в бота для установки таймера!\n\n'
        'Чтобы выбрать дату для таймера, выполните следующие шаги:\n'
        '1. Нажмите на кнопку с датой, чтобы выбрать нужный день.\n'
        '2. Используйте кнопки "<<"" и ">>", чтобы перемещаться между месяцами.\n'
        '3. После выбора даты таймер будет установлен, и вы получите уведомление, когда время истечет.\n\n'
        'Нажмите "Старт", чтобы начать выбор даты:',
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок для установки таймера."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('prev_month'):
        year, month = map(int, query.data.split('-')[1:])
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        keyboard = generate_calendar_buttons(year, month)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text('Выберите дату для таймера:', reply_markup=reply_markup)

    elif query.data.startswith('next_month'):
        year, month = map(int, query.data.split('-')[1:])
        month += 1
        if month > 12:
            month = 1
            year += 1
        keyboard = generate_calendar_buttons(year, month)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text('Выберите дату для таймера:', reply_markup=reply_markup)

    elif query.data == 'back':
        await start(update, context)  # Вернуться к выбору даты

    else:
        # Получаем выбранную дату
        selected_date = query.data
        target_date = datetime.strptime(selected_date, '%Y-%m-%d')

        await set_timer(target_date, query)

async def set_timer(target_date, query):
    """Устанавливает таймер на указанную дату и запускает его в отдельном потоке."""
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

def main():
    """Основная функция для запуска бота."""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
