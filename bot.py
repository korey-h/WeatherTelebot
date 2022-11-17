from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton,
    InlineKeyboardMarkup)

from datetime import datetime
import os

from config import MESSAGES
from models import User
from utils import MonthStat, Towns, collect_stat, html_parser

load_dotenv('.env')

bot = TeleBot(os.getenv('TOKEN'))
users = {}
weather_stat = {}
towns = Towns()


def get_user(message) -> User:
    user_id = message.chat.id
    return users.setdefault(user_id, User(id=user_id))


def try_exec_stack(user: User):
    command = user.cmd_stack_pop()
    if command and callable(command['cmd']):
        command['cmd'](command['data'])
    else:
        user.cmd_stack = command


def get_month_stat(town, town_name, year, month) -> MonthStat:
    mark = (town, year, month)
    if weather_stat.get(mark):
        return weather_stat.get(mark)
    param_list = [
        {'town_id': town, 'year': year,
         'month': month, 'town_name': town_name}]
    res = collect_stat(param_list, html_parser, MonthStat)
    weather_stat.update(res)
    return weather_stat[mark]


def make_base_kbd(lang='ru'):
    keyboard = ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
    but_town = KeyboardButton(MESSAGES[lang]['but_town'])
    but_year_ago = KeyboardButton(MESSAGES[lang]['but_year_ago'])
    but_decade = KeyboardButton(MESSAGES[lang]['but_decade'])
    keyboard.add(but_town, but_year_ago, but_decade)
    return keyboard


def make_cancel_keys(lang='ru'):
    keyboard = InlineKeyboardMarkup()
    but_cancel = InlineKeyboardButton(
        text=MESSAGES[lang]['cancel'],
        callback_data=MESSAGES[lang]['cancel'])
    return keyboard.add(but_cancel, )


def make_btn_rows(button_class, names: list,
                  data: list = None, rows: int = 3,
                  fill: bool = True) -> list:
    rows = 8 if rows > 8 else rows
    rows = 1 if rows < 1 else rows
    data = names if not data else data
    if fill:
        offset = rows - len(names) % rows
        marks = names + ['.' for x in range(offset)]
        values = data + [s for s in marks[len(data): len(marks)]]

    btn_line = []
    btn_rows = []
    for num, mark in enumerate(marks):
        if num % rows == 0 and num != 0:
            btn_rows.append(btn_line)
            btn_line = []
        btn = button_class(text=mark, callback_data=values[num])
        btn_line.append(btn)
    btn_rows.append(btn_line)
    return btn_rows


def make_month_keys(lang='ru', rows=5):
    names = ['янв', 'февр', 'март', 'апр', 'май', 'июнь',
             'июль', 'авг', 'сент', 'окт', 'нояб', 'дек']
    data = [str(x) for x in range(len(names))]
    buttons = make_btn_rows(InlineKeyboardButton, names, data, rows)
    return InlineKeyboardMarkup(keyboard=buttons)


@bot.message_handler(commands=['start'])
def welcome(message):
    user = get_user(message)
    keyboard = make_base_kbd(lang=user.lang)
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
        all_comm = [command['cmd_name'], ]
        while command:
            cmd = command['cmd']
            prev = user.cmd_stack_pop()
            if not prev or cmd != prev['calling']:
                user.cmd_stack = prev
                break
            all_comm.append(prev['cmd_name'])
        out = ', '.join(all_comm)
        bot.send_message(
            user.id,
            MESSAGES[user.lang]['cancel_mess'].format(out))


@bot.message_handler(commands=['год_назад'])
def get_year_ago(message):
    user = get_user(message)
    if user.town:
        now = datetime.now()
        day = int(now.strftime('%d'))
        month = int(now.strftime('%m'))
        year = int(now.strftime('%Y')) - 1
        stat = get_month_stat(user.town, user.town_name, year, month)
        data = stat.daystat(day, pretty=True, as_pic=True)
        if data:
            bot.send_photo(user.id, photo=data)
        else:
            bot.send_message(user.id, MESSAGES[user.lang]['no_data'])
    else:
        next = MESSAGES[user.lang]['but_town']
        name = MESSAGES[user.lang]['but_year_ago']
        user.cmd_stack = (name, get_year_ago, message, next)
        settown(message, user, next)


@bot.message_handler(commands=['десятилетие'])
def get_decade(message):
    user = get_user(message)
    if not user.town:
        user.cmd_stack = (message.text, get_decade, message)
        settown(message, user, MESSAGES[user.lang]['but_town'])
    elif not user.get_cmd_stack() or (
            user.get_cmd_stack()['cmd_name'] != message.text):
        keyboard = make_month_keys(lang=user.lang)
        bot.send_message(
            user.id,
            MESSAGES[user.lang]['mess_decade'],
            reply_markup=keyboard)


@bot.message_handler(content_types=["text"])
def auditor(message):
    user = get_user(message)
    last_command = user.cmd_stack_pop()
    if last_command and last_command['cmd_name'] == '/город':
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
            kwargs = {'reply_markup': make_cancel_keys(lang=user.lang)}
            bot.send_message(user.id, mess, **kwargs)
    else:
        user.cmd_stack = last_command


bot.polling(non_stop=True)
