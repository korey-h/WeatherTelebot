from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton,
    InlineKeyboardMarkup)

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


def try_exec_stack(user: User):
    command = user.cmd_stack_pop()
    if command and callable(command[0]):
        command[0](command[1])
    else:
        user.cmd_stack = command


def make_keyboard(lang='ru'):
    keyboard = ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
    but_town = KeyboardButton(MESSAGES[lang]['but_town'])
    but_year_ago = KeyboardButton(MESSAGES[lang]['but_year_ago'])
    keyboard.add(but_town, but_year_ago)
    return keyboard


def make_inline_keys(lang='ru'):
    keyboard = InlineKeyboardMarkup()
    but_cancel = InlineKeyboardButton(
        text=MESSAGES[lang]['cancel'],
        callback_data=MESSAGES[lang]['cancel']
    )

    keyboard.add(but_cancel, )
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
def settown(message, user=None, command=None):
    if not user:
        user = get_user(message)
    if not command:
        command = message.text
    user.cmd_stack = command
    bot.send_message(user.id, MESSAGES[user.lang]['settown'])


@bot.callback_query_handler(func=lambda call: True, )
def cancel_comm(call):
    user = get_user(call.message)
    if call.data == MESSAGES[user.lang]['cancel']:
        command = user.cmd_stack_pop()
        bot.send_message(
            user.id,
            MESSAGES[user.lang]['cancel_mess'].format(command[0]))


@bot.message_handler(commands=['год_назад'])
def get_year_ago(message):
    user = get_user(message)
    if user.town:
        now = datetime.now()
        day = int(now.strftime('%d'))
        month = int(now.strftime('%m'))
        year = int(now.strftime('%Y')) - 1
        stat = MonthStat(town_id=user.town, year=year,
                         month=month, town_name=user.town_name)
        data = stat.daystat(day, pretty=True, as_pic=True)
        if data:
            bot.send_photo(user.id, photo=data)
        else:
            bot.send_message(user.id, MESSAGES[user.lang]['no_data'])
    else:
        user.cmd_stack = (get_year_ago, message)
        settown(message, user, MESSAGES[user.lang]['but_town'])


@bot.message_handler(content_types=["text"])
def auditor(message):
    user = get_user(message)
    last_command = user.cmd_stack_pop()
    if last_command and last_command[0] == '/город':
        kwargs = {}
        town_id = towns.get_id(message.text)
        if town_id:
            user.town = town_id
            user.town_name = message.text.capitalize()
            mess = MESSAGES[user.lang]['town_finded']
            bot.send_message(user.id, mess, **kwargs)
            bot.send_chat_action(user.id, 'typing', 10)
            try_exec_stack(user)

        else:
            mess = MESSAGES[user.lang]['town_nothing']
            user.cmd_stack = last_command
            kwargs = {'reply_markup': make_inline_keys(lang=user.lang)}
            bot.send_message(user.id, mess, **kwargs)
    else:
        user.cmd_stack = last_command


bot.polling(non_stop=True)
