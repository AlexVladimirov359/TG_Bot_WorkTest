import datetime

import requests
from aiogram import executor, Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiohttp import ClientSession

from config import open_weather_token
from config import tg_bot_token

storage = MemoryStorage()
bot = Bot(tg_bot_token)
dp = Dispatcher(bot=bot,
                storage=storage)


def get_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Погода'))
    kb.add(KeyboardButton('Животные:3'))
    kb.add(KeyboardButton('Конвертер валют'))
    kb.add(KeyboardButton('Опросник'))

    return kb


def get_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('/cancel'))


def get_random_animal() -> ReplyKeyboardMarkup:
    ra = ReplyKeyboardMarkup(resize_keyboard=True)
    ra.add(KeyboardButton('Больше милоты'))
    ra.add(KeyboardButton('/cancel'))
    return ra


class ClientStatesGroup(StatesGroup):
    weather = State()
    desc = State()
    image = State()
    money = State()
    poll = State()
    options = State()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    await message.answer('Добро пожаловать, этот бот показывает погоду, милых животных,'
                         ' конвертирует валюты а так же создает опросы',
                         reply_markup=get_keyboard())


@dp.message_handler(commands=['cancel'], state='*')
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await message.reply('Чем займемся теперь?',
                        reply_markup=get_keyboard())
    await state.finish()


# -----------------------------------------------------------------------------


@dp.message_handler(Text(equals='Погода', ignore_case=True), state=None)
async def start_work(message: types.Message) -> None:
    await ClientStatesGroup.weather.set()
    await message.answer('Введите название города (RU/EU)',
                         reply_markup=get_cancel())


@dp.message_handler(lambda message: not message.text, state=ClientStatesGroup.weather)
async def check_city(message: types.Message):
    return await message.reply('Это не город')


@dp.message_handler(lambda message: message.text, content_types=['text'], state=ClientStatesGroup.weather)
async def load_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

        code_to_smile = {
            "Clear": "Ясно \U00002600",
            "Clouds": "Облачно \U00002601",
            "Rain": "Дождь \U00002614",
            "Drizzle": "Дождь \U00002614",
            "Thunderstorm": "Гроза \U000026A1",
            "Snow": "Снег \U0001F328",
            "Mist": "Туман \U0001F32B"
        }

        try:
            r = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={open_weather_token}&units=metric"
            )
            data = r.json()

            city = data["name"]
            cur_weather = data["main"]["temp"]

            weather_description = data["weather"][0]["main"]
            if weather_description in code_to_smile:
                wd = code_to_smile[weather_description]
            else:
                wd = "Посмотри в окно, не пойму что там за погода!"

            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]
            wind = data["wind"]["speed"]
            sunrise_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
            sunset_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunset"])
            length_of_the_day = datetime.datetime.fromtimestamp(
                data["sys"]["sunset"]) - datetime.datetime.fromtimestamp(
                data["sys"]["sunrise"])

            await message.reply(f"***{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}***\n"
                                f"Погода в городе: {city}\nТемпература: {cur_weather}C° {wd}\n"
                                f"Влажность: {humidity}%\nДавление: {pressure} мм.рт.ст\nВетер: {wind} м/с\n"
                                f"Восход солнца: {sunrise_timestamp}\nЗакат солнца: {sunset_timestamp}\nПродолжительность дня: {length_of_the_day}\n"
                                f"***Хорошего дня!***"
                                )
            await message.answer(f'Вы можете указать следующий город ниже или так же вернуться в меню кнопкой /cancel')

        except:
            await message.reply("\U00002620 Проверьте название города \U00002620")


@dp.message_handler(lambda message: message.photo, content_types=['text'], state=ClientStatesGroup.weather)
async def your_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    await ClientStatesGroup.next()
    await message.reply('А теперь отправь нам описание!')


@dp.message_handler(state=ClientStatesGroup.desc)
async def your_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['desc'] = message.text

    await message.reply('Попробуйте указать город на английском')

    async with state.proxy() as data:
        await bot.send_photo(chat_id=message.from_user.id,
                             photo=data['photo'],
                             caption=data['desc'])

    await state.finish()


# ------------------------------------------------------------------------------------

@dp.message_handler(Text(equals='Животные:3', ignore_case=True), state=None)
async def start_image(message: types.Message) -> None:
    await ClientStatesGroup.image.set()
    await message.answer('Вам нужно больше милоты?',
                         reply_markup=get_random_animal())


# Отправка случайной картинки
@dp.message_handler(lambda message: message.text, content_types=['text'], state=ClientStatesGroup.image)
async def send_random_image(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    url = "https://api.unsplash.com/photos/random?query=cute-animals&client_id" \
          "=C1Xsx4Ze0lWWU9oYrqVAeGS0wsXAG8IK9Q7I1DuIb7o"
    async with ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "urls" not in data:
                await message.reply("Не удалось получить картинку. Попробуйте еще раз.")
                return
            image_url = data["urls"]["small"]
            await message.reply_photo(image_url)


@dp.message_handler(commands=['Больше милоты'], state=ClientStatesGroup.image)
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await message.reply('Больше милоты',
                        reply_markup=get_keyboard())
    await state.finish()


# --------------------------------------------------------------------------------------

@dp.message_handler(Text(equals='Конвертер валют', ignore_case=True), state=None)
async def start_image(message: types.Message) -> None:
    await ClientStatesGroup.money.set()
    await message.answer('Введите сумму и пару валют, например: 100 USD to EUR',
                         reply_markup=get_cancel())


@dp.message_handler(lambda message: message.text, content_types=['text'], state=ClientStatesGroup.money)
async def convert_currency(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    query = message.text.split()
    if len(query) != 4 or query[1].upper() not in ["USD", "EUR", "RUB"] or query[3].upper() not in ["USD", "EUR",
                                                                                                    "RUB"]:
        await message.reply("Неверный формат запроса. Введите сумму и пару валют, например: 100 USD to EUR")
        return
    amount, base_currency, _, target_currency = query
    amount = float(amount)
    url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
    async with ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "rates" not in data:
                await message.reply("Не удалось получить информацию о курсе валют. Попробуйте еще раз.")
                return
            rate = data["rates"][target_currency.upper()]
            converted_amount = round(amount * rate, 2)
            await message.reply(f"{amount} {base_currency.upper()} = {converted_amount} {target_currency.upper()}")


# ------------------------------------------------------------------------------------------------------------------
# создание машино состояния для Опросов
@dp.message_handler(Text(equals='Опросник', ignore_case=True), state=None)
async def start_poll(message: types.Message) -> None:
    await ClientStatesGroup.poll.set()
    await message.answer('Задайте тему опроса',
                         reply_markup=get_cancel())


# Задаем параметры опроса сразу используя два состояния
@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.poll)
async def process_poll(message: types.Message, state: FSMContext):
    question = message.text
    await state.update_data(question=question)

    await ClientStatesGroup.next()
    await bot.send_message(message.chat.id, "Введите варианты ответов через запятую (,):")


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.poll)
async def create_poll(message: types.Message, question=None):
    options = ["Опция 1", "Опция 2", "Опция 3"]
    await bot.send_poll(chat_id=message.chat.id, question="Ваш вопрос здесь", options=options, is_anonymous=False)
    await bot.send_poll(message.chat.id, question, options)


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.options)
async def process_poll_options(message: types.Message, state: FSMContext):
    options = message.text.split(',')
    user_data = await state.get_data()
    question = user_data['question']
    await bot.send_poll(message.chat.id, question, options)
    await message.answer('Отлично вы создали опрос!',
                         reply_markup=get_cancel())


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True)
