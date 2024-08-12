import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Инициализация бота и диспетчера
bot_token = ""
admin_ids = [1, 2]
group_id = 

bot = Bot(token=bot_token)
dp = Dispatcher(bot)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
conn = sqlite3.connect('giveaway.db')
cursor = conn.cursor()

# Создание таблиц, если они не существуют
cursor.execute('''CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    number INTEGER,
                    message_id INTEGER,
                    disqualified BOOLEAN DEFAULT 0)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER)''')

conn.commit()

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_giveaway(message: types.Message):
    if message.from_user.id in admin_ids and message.chat.id == group_id:  # Проверка на админа
        # Удаление команды
        await bot.delete_message(message.chat.id, message.message_id)
        
        # Задержка перед запуском розыгрыша
        await asyncio.sleep(10)
        
        # Удаление предыдущих участников
        cursor.execute('DELETE FROM participants')
        conn.commit()

        # Отправка сообщения о запуске розыгрыша в группе
        await bot.send_message(
            group_id,
            "<b>🎉 Розыгрыш запущён!</b>",  # Жирный шрифт с использованием HTML
            parse_mode="HTML"
        )
        logging.info("Розыгрыш запущен")

        # Уведомление всех пользователей, которые взаимодействовали с ботом
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        for user in users:
            try:
                await bot.send_message(user[0], "🎉 Розыгрыш запущен. Присоединяйтесь в группу и отправляйте свои числа.")
            except Exception as e:
                logging.warning(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")

# Обработчик команды /stop
@dp.message_handler(commands=['stop'])
async def stop_giveaway(message: types.Message):
    if message.from_user.id in admin_ids and message.chat.id == group_id:  # Проверка на админа
        # Удаление команды
        await bot.delete_message(message.chat.id, message.message_id)

        # Отправка сообщения о завершении розыгрыша
        await bot.send_message(
            group_id,
            "<b>⏳ Розыгрыш завершён. Ожидайте итогов!</b>",  # Жирный шрифт с использованием HTML
            parse_mode="HTML"
        )
        logging.info("Розыгрыш завершён")

        # Уведомление всех пользователей о завершении розыгрыша
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        for user in users:
            try:
                await bot.send_message(user[0], "⏳ Розыгрыш завершён. Ожидайте объявления победителей.")
            except Exception as e:
                logging.warning(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")

# Обработчик команды /true <число>
@dp.message_handler(commands=['true'])
async def determine_winner(message: types.Message):
    if message.from_user.id in admin_ids and message.chat.id == group_id:  # Проверка на админа
        # Удаление команды
        await bot.delete_message(message.chat.id, message.message_id)
        
        try:
            target_number = int(message.get_args())
            await asyncio.sleep(10)  # Пауза в 10 секунд без уведомления

            cursor.execute('SELECT user_id, username, number, message_id FROM participants WHERE disqualified = 0 ORDER BY ABS(number - ?)', (target_number,))
            participants = cursor.fetchall()

            if participants:
                winner = participants[0]
                nearest = participants[1:11]

                winner_link = f"[{winner[1]}](tg://user?id={winner[0]})"
                number_link = f"[{winner[2]}](https://t.me/c/{str(group_id)[4:]}/{winner[3]})"
                result_text = (f"Победитель выявлен:\n\n"
                               f"Имя победителя: {winner_link}\n"
                               f"Число, отправленное победителем: {number_link}\n\n"
                               f"Почти приблизились:\n")
                
                for user in nearest:
                    user_link = f"[{user[1]}](tg://user?id={user[0]})"
                    number_link = f"[{user[2]}](https://t.me/c/{str(group_id)[4:]}/{user[3]})"
                    result_text += f"{user_link} с числом {number_link}\n"
                
                await bot.send_message(group_id, result_text, parse_mode="Markdown")
                logging.info(f"Результаты отправлены: {result_text}")

                # Уведомление всех пользователей о результатах розыгрыша
                cursor.execute('SELECT user_id FROM users')
                users = cursor.fetchall()
                for user in users:
                    try:
                        await bot.send_message(user[0], "🏆 Победители розыгрыша объявлены! Проверьте группу для деталей.")
                    except Exception as e:
                        logging.warning(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")

            else:
                await bot.send_message(group_id, "🚫 Нет зарегистрированных участников или все участники дисквалифицированы.")
                logging.info("Нет зарегистрированных участников или все участники дисквалифицированы")
        except ValueError:
            await bot.send_message(group_id, "❗ Неверный формат команды. Используйте /true <число>")
            logging.error("Ошибка в формате команды")

# Обработчик на изменение сообщений
@dp.edited_message_handler(lambda message: message.text.isdigit())
async def handle_edited_message(message: types.Message):
    if message.chat.id == group_id:
        user_id = message.from_user.id
        cursor.execute('UPDATE participants SET disqualified = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        await message.answer("🚫 Вы дисквалифицированы из розыгрыша за изменение сообщения.")
        logging.warning(f"Пользователь {message.from_user.username} ({user_id}) дисквалифицирован за изменение сообщения")

# Обработчик чисел
@dp.message_handler(lambda message: message.text.isdigit())
async def register_number(message: types.Message):
    if message.chat.id == group_id:  # Проверяем, что сообщение пришло из нужной группы
        user_id = message.from_user.id
        username = message.from_user.username
        number = int(message.text)
        message_id = message.message_id

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone() is None:
            cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
            conn.commit()

        cursor.execute('SELECT * FROM participants WHERE user_id = ?', (user_id,))
        existing_entry = cursor.fetchone()

        if existing_entry is None:
            cursor.execute('INSERT INTO participants (user_id, username, number, message_id) VALUES (?, ?, ?, ?)', (user_id, username, number, message_id))
            logging.info(f"Число {number} зарегистрировано для пользователя: {username} ({user_id})")
        else:
            await message.answer("🔁 Вы уже отправили число. Повторное участие невозможно.")
            logging.info(f"Пользователь {username} ({user_id}) попытался отправить второе число")

        conn.commit()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
