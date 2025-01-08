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
    CallbackQueryHandler,
    MessageHandler,
    filters
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с кнопками выбора даты для таймера."""
    global current_date
    keyboard = generate_calendar_buttons(current_date.year, current_date.month)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Добро пожаловать в бота для установки таймера!\n\n'
        'Чтобы выбрать дату для таймера, выполните следующие шаги:\n'
        '1. Нажмите на кнопку с датой, чтобы выбрать нужный день.\n'
        '2. Используйте кнопки "<<"" и ">>", чтобы перемещаться '
        'между месяцами.\n'
        '3. После выбора даты и времени таймер будет установлен, '
        'и вы получите уведомление, когда время истечет.\n\n'
        'Нажмите "Старт", чтобы начать выбор даты:',
        reply_markup=reply_markup
    )


async def timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с инструкцией по установке таймера."""
    await update.message.reply_text(
        "Используйте команду /timer <время в днях>, чтобы установить таймер."
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
        await query.message.edit_text(
            'Выберите дату для таймера:',
            reply_markup=reply_markup
        )

    elif query.data.startswith('next_month'):
        year, month = map(int, query.data.split('-')[1:])
        month += 1
        if month > 12:
            month = 1
            year += 1
        keyboard = generate_calendar_buttons(year, month)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            'Выберите дату для таймера:',
            reply_markup=reply_markup
        )

    elif query.data == 'back':
        await start(update, context)  # Вернуться к выбору даты

    elif query.data.startswith('date_'):
        # Получаем выбранную дату
        selected_date = query.data.split('_')[1]
        target_date = datetime.strptime(selected_date, '%Y-%m-%d')

        # Запрашиваем точное время
        await query.message.reply_text(
            "Пожалуйста, выберите время для установки таймера "
            "или введите его в формате ЧЧ:ММ:",
            reply_markup=generate_time_keyboard()
        )
        context.user_data['target_date'] = target_date  # Сохраняем дату для дальнейшего использования
        return

    elif query.data.startswith('time_'):
        # Получаем выбранное время
        time_str = query.data.split('_')[1]
        await set_timer(context, query, time_str)
        return


async def set_timer(context, query, time_str):
    """Устанавливает таймер на основе выбранного или введенного времени."""
    target_date = context.user_data['target_date']
    event_time = int((target_date - datetime.now()).total_seconds())

    if event_time > 24 * 3600:  # Если таймер больше одного дня
        await query.message.reply_text(
            "Таймер установлен на более чем один день. "
            "Хотите установить конкретное время? (да/нет)"
        )
        context.user_data['waiting_for_time_confirmation'] = True
        return

    if time_str == "manual":
        await query.message.reply_text(
            "Пожалуйста, введите время в формате ЧЧ:ММ:"
        )
        return

    hour, minute = map(int, time_str.split(':'))
    target_date = target_date.replace(hour=hour, minute=minute)

    event_time = int((target_date - datetime.now()).total_seconds())

    message = await query.message.reply_text(
        f"Таймер установлен на {target_date.strftime('%Y-%m-%d %H:%M')}."
    )

    threading.Thread(
        target=run_timer,
        args=(event_time, query.message.chat_id, message.message_id, context)
    ).start()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для установки таймера вручную."""
    user_input = update.message.text
    if 'waiting_for_time_confirmation' in context.user_data:
        if user_input.lower() == "да":
            await update.message.reply_text(
                "Пожалуйста, выберите время для установки таймера "
                "или введите его в формате ЧЧ:ММ:"
            )
            return
        elif user_input.lower() == "нет":
            target_date = context.user_data['target_date']
            event_time = int((target_date - datetime.now()).total_seconds())
            message = await update.message.reply_text(
                f"Таймер установлен на {target_date.strftime('%Y-%m-%d')} "
                "без указания времени."
            )

            threading.Thread(
                target=run_timer,
                args=(event_time, update.message.chat_id, message.message_id, context)
            ).start()
            del context.user_data['waiting_for_time_confirmation']
            return
        else:
            await update.message.reply_text(
                "Пожалуйста, ответьте 'да' или 'нет'."
            )
            return

    try:
        hour, minute = map(int, user_input.split(':'))
        if 0 <= hour < 24 and 0 <= minute < 60:
            target_date = context.user_data['target_date'].replace(
                hour=hour,
                minute=minute
            )
            event_time = int((target_date - datetime.now()).total_seconds())

            message = await update.message.reply_text(
                f"Таймер установлен на {target_date.strftime('%Y-%m-%d %H:%M')}."
            )

            threading.Thread(
                target=run_timer,
                args=(event_time, update.message.chat_id, message.message_id, context)
            ).start()
        else:
            await update.message.reply_text(
                "Пожалуйста, введите время в правильном формате ЧЧ:ММ."
            )
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите время в правильном формате ЧЧ:ММ."
        )


def generate_time_keyboard():
    """
    Генерирует клавиатуру для выбора времени и добавляет
    кнопку для ручного ввода.
    """
    keyboard = []
    for hour in range(24):
        for minute in [0, 30]:  # Выбор только полных часов и половин
            time_str = f"{hour:02d}:{minute:02d}"
            keyboard.append([InlineKeyboardButton(
                time_str, callback_data=f'time_{time_str}')]
            )

    # Добавляем кнопку для ручного ввода времени
    keyboard.append([InlineKeyboardButton(
        "Введите время вручную", callback_data='time_manual')]
    )
    return InlineKeyboardMarkup(keyboard)


def run_timer(event_time, chat_id, message_id, context):
    """Запускает таймер и отправляет сообщение по его истечении."""
    time.sleep(event_time)
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="Таймер завершен! Время события истекло!"
    )
    send_notifications(chat_id, event_time, context)


def send_notifications(chat_id, event_time, context):
    """Отправляет уведомления о приближающемся событии."""
    target_date = datetime.now() + timedelta(seconds=event_time)

    # Логика уведомлений
    if event_time > 6 * 30 * 24 * 3600:  # Более 6 месяцев
        intervals = [
            60 * 24 * 3600,
            60 * 24 * 3600 * 2,
            7 * 24 * 3600,
            3 * 24 * 3600,
            24 * 3600
        ]
    else:  # Менее 6 месяцев
        intervals = [
            30 * 24 * 3600,
            7 * 24 * 3600,
            3 * 24 * 3600,
            24 * 3600
        ]

    for interval in intervals:
        time.sleep(event_time - interval)  # Ждем до следующего уведомления
        context.bot.send_message(
            chat_id=chat_id, text="Напоминание: событие приближается!"
        )


def generate_calendar_buttons(year, month):
    """Генерирует кнопки для выбора даты в виде календаря."""
    keyboard = []
    month_start = datetime(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    year_end = year if month < 12 else year + 1
    month_end = (datetime(year_end, next_month, 1) - timedelta(days=1)).day

    # Добавляем заголовок с днями недели
    keyboard.append([
        InlineKeyboardButton("Пн", callback_data='ignore'),
        InlineKeyboardButton("Вт", callback_data='ignore'),
        InlineKeyboardButton("Ср", callback_data='ignore'),
        InlineKeyboardButton("Чт", callback_data='ignore'),
        InlineKeyboardButton("Пт", callback_data='ignore'),
        InlineKeyboardButton("Сб", callback_data='ignore'),
        InlineKeyboardButton("Вс", callback_data='ignore')
    ])

    # Заполняем кнопки датами
    day = 1
    while day <= month_end:
        row = []
        for _ in range(7):  # 7 дней в неделе
            if day <= month_end:
                row.append(InlineKeyboardButton(
                    day, callback_data=f'date_{year}-{month:02d}-{day:02d}')
                )
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


def main():
    """Основная функция для запуска бота."""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("timer", timer))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message)
    )

    application.run_polling()


if __name__ == '__main__':
    main()
