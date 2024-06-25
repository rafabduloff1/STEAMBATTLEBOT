import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import acc
import abr

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.getLevelName(logging.INFO))


# Инициализация бота и диспетчера
TOKEN = ''
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение к базе данных SQLite
conn = sqlite3.connect('steam_accounts.db')
cursor = conn.cursor()

# Создание таблиц, если они не существуют
cursor.execute("""CREATE TABLE IF NOT EXISTS accounts
                  (game_name TEXT PRIMARY KEY, account TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS abbreviations
                  (full_name TEXT PRIMARY KEY, abbreviation TEXT)""")
conn.commit()

# Функция для заполнения базы данных данными из файлов acc.py и abr.py
def populate_database():
    # Заполнение таблицы accounts
    cursor.execute("DELETE FROM accounts")  # Очистка таблицы перед заполнением
    for game_name, account in acc.game_accounts.items():
        cursor.execute("INSERT INTO accounts (game_name, account) VALUES (?, ?)", (game_name, account))

    # Заполнение таблицы abbreviations
    cursor.execute("DELETE FROM abbreviations")  # Очистка таблицы перед заполнением
    for full_name, abbreviation in abr.abbreviations.items():
        cursor.execute("INSERT INTO abbreviations (full_name, abbreviation) VALUES (?, ?)", (full_name, abbreviation))

    conn.commit()

# Заполнение базы данных данными из файлов acc.py и abr.py


# Состояния для машины состояний
class Form(StatesGroup):
    game_request = State()
    abbreviation_request = State()
    game_submission = State()

# Обработчик команды /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = KeyboardButton("Как писать игры?")
    btn2 = KeyboardButton("Поиск аккаунтов")
    btn3 = KeyboardButton("Поиск аббревиатур")
    btn4 = KeyboardButton("Заявка")
    btn5 = KeyboardButton("Как использовать аккаунты")
    keyboard.add(btn1, btn2, btn3, btn4, btn5)
    await message.reply("Выберите опцию:", reply_markup=keyboard)

# Обработчик кнопки "Как писать игры?"
@dp.message_handler(lambda message: message.text == "Как писать игры?")
async def guide(message: types.Message):
    await message.reply("Пишите названия полностью, включая '; . и другие символы. "
                        "Пример: Spider-Man: Miles Morales; marvel's avengers; assassin's creed black flag. "
                        "Также, если цифры в названии арабские, а последующего названия нет (Пример: GTA V), "
                        "то пишите цифру обычной. Пример: GTA 5. Если же продолжение есть, (Пример Assassin's Creed: IV Black Flag), "
                        "то пишите просто Assassin's Creed: Black Flag.")

# Обработчик кнопки "Как использовать аккаунты"
@dp.message_handler(lambda message: message.text == "Как использовать аккаунты")
async def use_guide(message: types.Message):
    await message.reply("Заходите на аккаунт, если надо вводите семейный пин, скачиваете игру, затем "
                        "нажимаете на надпись Steam в левом верхнем углу экрана"
                        ", включаете автономный режим, выключаете Remote play в настройках и играете")

# Обработчик кнопки "Поиск аккаунтов"
@dp.message_handler(lambda message: message.text == "Поиск аккаунтов")
async def handle_game_request(message: types.Message):
    await message.reply("Введите название игры:")
    await Form.game_request.set()

@dp.message_handler(state=Form.game_request)
async def search_account(message: types.Message, state: FSMContext):
    populate_database()
    game_name = message.text.lower()
    cursor.execute("SELECT account FROM accounts WHERE game_name = ?", (game_name,))
    result = cursor.fetchone()
    if result:
        account = result[0]
        account_parts = account.split(":")
        account_start = account_parts[0]
        account_end = account_parts[1]
        pin = account_parts[2] if len(account_parts) > 2 else ""
        if pin:
            await message.reply(f"Ваш аккаунт для {game_name}:\n`{account_start}`:`{account_end}`:`{pin}`\n\(логин:пароль:пин\)", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await message.reply(f"Ваш аккаунт для {game_name}:\n`{account_start}`:`{account_end}`\n\(логин:пароль\)", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await message.reply(f"Извините, аккаунт для {game_name} не найден.")
    await state.finish()

# Обработчик кнопки "Поиск аббревиатур"
@dp.message_handler(lambda message: message.text == "Поиск аббревиатур")
async def abbreviation_request(message: types.Message):
    await message.reply("Введите игру для аббревиатуры:")
    await Form.abbreviation_request.set()

# Обработчик ввода названия игры для поиска аббревиатуры
@dp.message_handler(state=Form.abbreviation_request)
async def search_abbreviation(message: types.Message, state: FSMContext):
    abbr_name = message.text.lower()
    cursor.execute("SELECT abbreviation FROM abbreviations WHERE full_name = ?", (abbr_name,))
    result = cursor.fetchone()
    if result:
        abbreviation = result[0]
        await message.reply(f"Аббревиатура для {abbr_name}: {abbreviation}")
    else:
        await message.reply(f"Аббревиатура для {abbr_name} не найдена.")
    await state.finish()

# Обработчик кнопки "Заявка"
@dp.message_handler(lambda message: message.text == "Заявка")
async def request_game(message: types.Message):
    await message.reply("Напишите игру для заявки:")
    await Form.game_submission.set()

# Обработчик ввода названия игры для заявки
@dp.message_handler(state=Form.game_submission)
async def handle_request(message: types.Message, state: FSMContext):
    game_request = message.text
    with open("requests.txt", "a") as file:
        file.write(f"{message.from_user.id}: {game_request}\n")
    await message.reply("Ваша заявка принята.")
    await state.finish()

# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)