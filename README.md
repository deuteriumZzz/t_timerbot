# Telegram Timer Bot

Этот бот для Telegram позволяет пользователям устанавливать таймеры на определенные даты. Пользователи могут выбирать даты через кнопки или вводить их вручную.

## Установка

1. **Клонируйте репозиторий:**

   ```bash
   git clone https://github.com/yourusername/telegram-timer-bot.git
   cd telegram-timer-bot
   ```

2. **Создайте и активируйте виртуальное окружение (опционально):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/Mac
   venv\Scripts\activate  # Для Windows
   ```

3. **Установите необходимые библиотеки:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Создайте файл `.env`:**

   В корневом каталоге вашего проекта создайте файл `.env` и добавьте в него ваш токен бота:

   ```plaintext
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   ```

   Замените `ваш_токен_бота` на токен, который вы получили от [BotFather](https://core.telegram.org/bots#botfather).

5. **Добавьте `.env` в `.gitignore`:**

   Убедитесь, что файл `.env` добавлен в `.gitignore`, чтобы избежать случайной публикации токена в репозитории:

   ```plaintext
   # .gitignore
   .env
   ```