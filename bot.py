from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from datetime import datetime
import os

from config import MESSAGES
from models import User
from utils import MonthStat, Towns

load_dotenv('.env')

bot = TeleBot(os.getenv('TOKEN'))
users = {}
towns = Towns()


def get_user(message) -> User:
    user_id = message.chat.id
    return users.setdefault(user_id, User(id=user_id))


def make_keyboard(lang='ru'):
    keyboard = ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
    but_town = KeyboardButton(MESSAGES[lang]['but_town'])
    but_year_ago = KeyboardButton(MESSAGES[lang]['but_year_ago'])
    keyboard.add(but_town, but_year_ago)
    return keyboard


@bot.message_handler(commands=['start'])
def welcome(message):
    user = get_user(message)
    keyboard = make_keyboard(lang=user.lang)
    bot.send_message(
        user.id,
        MESSAGES[user.lang]['welcome'],
        reply_markup=keyboard)


@bot.message_handler(commands=['город'])
def settown(message):
    user = get_user(message)
    user.last_req = message.text
    bot.send_message(user.id, MESSAGES[user.lang]['settown'])


@bot.message_handler(commands=['год_назад'])
def get_year_ago(message):
    user = get_user(message)
    user.last_req = message.text
    if user.town:
        now = datetime.now()
        day = int(now.strftime('%d'))
        month = int(now.strftime('%m'))
        year = int(now.strftime('%Y')) - 1
        stat = MonthStat(town_id=user.town, year=year, month=month)
        data = stat.daystat(day, pretty=True, as_pic=True)
        if data:
            # bot.send_message(user.id, f'<pre>{data}</pre>', parse_mode='html')
            bot.send_photo(user.id, photo=data, parse_mode='html')
        else:
            bot.send_message(user.id, MESSAGES[user.lang]['no_data'])


@bot.message_handler(content_types=["text"])
def auditor(message):
    user = get_user(message)
    last_command = user.last_req
    if last_command == '/город':
        town_id = towns.get_id(message.text)
        if town_id:
            user.town = town_id
            mess = MESSAGES[user.lang]['town_finded']
        else:
            mess = MESSAGES[user.lang]['town_nothing']
        bot.send_message(user.id, mess)


bot.polling(non_stop=True)
