# scheduling

Telegram bot project on Python.

Telegram-бот для управления расписаниями пятниц и воскресений. Правила перенесены из `scheduling.php`: лимиты по типам дней, запрет первых двух слотов, одиночное участие, только воскресенье, интервал между назначениями и проверка итогового расписания.

## Создание бота в Telegram

1. Откройте Telegram и напишите `@BotFather`.
2. Выполните `/newbot`.
3. Задайте имя и username бота.
4. Скопируйте токен в файл `.env`.

## Установка

```bash
cd /home/d/doberalex/public_html/scheduling
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

```bash
BOT_TOKEN=telegram_token_from_botfather
ADMIN_IDS=62602216
TIMEZONE=Europe/Moscow
DB_HOST=localhost
DB_PORT=3306
DB_USER=doberalex_tbotschedule
DB_PASSWORD=database_password
DB_NAME=doberalex_tbotschedule
```

Все рабочие данные хранятся в MySQL. Бот сам создаёт таблицы при первом запуске:

- `schedule_participants`
- `schedule_limits`
- `schedule_participant_lists`
- `schedule_extra_dates`

Явная инициализация базы:

```bash
python3 scripts/init_db.py
```

## Запуск

```bash
python3 run.py
```

Для фонового запуска:

```bash
chmod +x run_bot.sh
./run_bot.sh
```

## Команды

- `/schedule` - расписание на текущий месяц.
- `/schedule 7 2026` - расписание на указанный месяц.
- `/settings` - текущие настройки.
- `/participants` - список участников.
- `/add_name Имя` - добавить участника.
- `/remove_name Имя` - удалить участника.
- `/blocked add Имя` или `/blocked remove Имя` - список `blockedStart`.
- `/single add Имя` или `/single remove Имя` - список `singleParticipation`.
- `/only_sunday add Имя` или `/only_sunday remove Имя` - список `onlySunday`.
- `/limit fri 3` или `/limit sun 5` - лимиты.
- `/extra fri add 15.07.2026` или `/extra sun remove 19.07.2026` - дополнительные даты.

## Git

Remote:

```bash
git@github.com:doberalex/scheduling.git
```
