from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton,
    InlineKeyboardMarkup)

from datetime import datetime
import os

from config import MESSAGES
from models import User
from utils import MonthStat, Towns, collect_stat, html_parser, day_for_years

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
        command['cmd'](**command['data'])
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
    data = [str(x) for x in range(1, len(names) + 1)]
    buttons = make_btn_rows(InlineKeyboardButton, names, data, rows)
    return InlineKeyboardMarkup(keyboard=buttons)


def make_day_keys(month: int, lang: str = 'ru', rows: int = 7):
    verge = 31
    if month in (4, 6, 9, 11):
        verge = 30
    elif month == 2:
        verge = 28
    names = [x for x in range(1, verge + 1)]
    data = [x for x in range(1, verge + 1)]
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
def settown(message, user=None):
    _NAME = 'town'
    if not user:
        user = get_user(message)
    user.cmd_stack = (_NAME, settown, {'message': message})
    bot.send_message(user.id, MESSAGES[user.lang]['settown'])


@bot.callback_query_handler(func=lambda call: True, )
def inline_keys_exec(call):
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
    else:
        up_stack = user.get_cmd_stack()
        if up_stack and up_stack['cmd'] and up_stack['cmd_name']:
            up_stack['data']['text'] = call.data
            user.cmd_stack = up_stack
        try_exec_stack(user)


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
        user.cmd_stack = (name, get_year_ago, {'message': message}, next)
        settown(message, user)


@bot.message_handler(commands=['десятилетие'])
def get_decade(*args, **kwargs):
    _NAME = 'decade'
    message = kwargs['message'] if not args else args[0]
    user = get_user(message)
    up_stack = user.get_cmd_stack()
    if not user.town:
        user.cmd_stack = (_NAME, get_decade, {'message': message})
        settown(message, user)
    elif not up_stack or (
            up_stack['cmd_name'] != _NAME and
            not up_stack['data'].get('text') and
            not up_stack['data'].get('month')):
        user.cmd_stack = (_NAME, get_decade, {'message': message})
        keyboard = make_month_keys(lang=user.lang)
        bot.send_message(
            user.id,
            MESSAGES[user.lang]['mess_decade'],
            reply_markup=keyboard)
    elif not up_stack['data'].get('day') and (
            not up_stack['data'].get('month')):
        up_stack['data']['month'] = int(up_stack['data']['text'])
        keyboard = make_day_keys(month=up_stack['data']['month'],
                                 lang=user.lang)
        bot.send_message(
            user.id,
            MESSAGES[user.lang]['mess_get_day'],
            reply_markup=keyboard)
    elif not up_stack['data'].get('day'):
        day = int(up_stack['data']['text'])
        month = up_stack['data']['month']
        bot.send_message(user.id, "Произвожу сбор статистики.")
        bot.send_chat_action(user.id, 'typing', 10)
        stat = day_for_years(town_id=user.town, town_name=user.town_name,
                             day=day, month=month)
        bot.send_photo(user.id, photo=MonthStat._text_to_image(stat))
        user.cmd_stack_pop()
        try_exec_stack(user)


@bot.message_handler(content_types=["text"])
def auditor(message):
    user = get_user(message)
    last_command = user.cmd_stack_pop()
    if last_command and last_command['cmd_name'] == 'town':
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
        try_exec_stack(user)


bot.polling(non_stop=True)
