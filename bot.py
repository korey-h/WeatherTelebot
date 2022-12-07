from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton,
    InlineKeyboardMarkup)

from datetime import datetime
import os

from config import MESSAGES
from models import User
from utils import (
    MonthStat, Towns,
    collect_stat, html_parser, day_for_years, stat_week_before,
    comm_from_text)


load_dotenv('.env')
with open('about.txt', encoding='utf-8') as f:
    ABOUT = f.read()

bot = TeleBot(os.getenv('TOKEN'))
users = {}
weather_stat = {}
towns = Towns()


def get_user(message) -> User:
    user_id = message.chat.id
    return users.setdefault(user_id, User(id=user_id))


def try_exec_stack(user: User):
    command = user.get_cmd_stack()
    if command and callable(command['cmd']):
        command['cmd'](**command['data'])


def get_month_stat(town, town_name, year, month) -> MonthStat:
    mark = (town, year, month)
    mon = weather_stat.get(mark)
    if mon and not mon.need_upd:
        return weather_stat.get(mark)
    param_list = [
        {'town_id': town, 'year': year,
         'month': month, 'town_name': town_name}]
    res = collect_stat(param_list, html_parser, MonthStat)
    weather_stat.update(res)
    return weather_stat[mark]


def make_base_kbd():
    keyboard = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = [
        KeyboardButton(MESSAGES['but_town']),
        KeyboardButton(MESSAGES['but_date']),
        KeyboardButton(MESSAGES['but_year_ago']),
        KeyboardButton(MESSAGES['but_decade']),
        KeyboardButton(MESSAGES['but_week']),
        KeyboardButton(MESSAGES['but_clear']),
        KeyboardButton(MESSAGES['but_about'])]
    return keyboard.add(*buttons)


def make_cancel_keys():
    keyboard = InlineKeyboardMarkup()
    but_cancel = InlineKeyboardButton(
        text=MESSAGES['cancel'],
        callback_data='cancel')
    return keyboard.add(but_cancel, )


def make_pass_keys():
    keyboard = InlineKeyboardMarkup()
    but_cancel = InlineKeyboardButton(
        text=MESSAGES['but_pass'],
        callback_data='pass')
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


def make_month_keys(rows=5):
    names = ['янв', 'февр', 'март', 'апр', 'май', 'июнь',
             'июль', 'авг', 'сент', 'окт', 'нояб', 'дек']
    data = [str(x) for x in range(1, len(names) + 1)]
    buttons = make_btn_rows(InlineKeyboardButton, names, data, rows)
    but_cancel = InlineKeyboardButton(text=MESSAGES['cancel'],
                                      callback_data='cancel')
    buttons.append([but_cancel])
    return InlineKeyboardMarkup(keyboard=buttons)


def make_day_keys(month: int, rows: int = 7):
    verge = 31
    if month in (4, 6, 9, 11):
        verge = 30
    elif month == 2:
        verge = 28
    names = [x for x in range(1, verge + 1)]
    data = [x for x in range(1, verge + 1)]
    buttons = make_btn_rows(InlineKeyboardButton, names, data, rows)
    but_cancel = InlineKeyboardButton(text=MESSAGES['cancel'],
                                      callback_data='cancel')
    but_chg_mon = InlineKeyboardButton(text=MESSAGES['but_chg_mon'],
                                       callback_data='chg_month')
    buttons.append([but_cancel, but_chg_mon])
    return InlineKeyboardMarkup(keyboard=buttons)


def stat_transm(user, stat_func, params):
    bot.send_message(user.id, "Произвожу сбор статистики.")
    bot.send_chat_action(user.id, 'typing', 10)
    stat = stat_func(**params)
    if stat:
        photo = MonthStat._text_to_image(stat['table'])
        if photo:
            bot.send_photo(user.id, photo=photo)
        else:
            bot.send_message(user.id, MESSAGES['big_photo'])
        if stat.get('file'):
            bot.send_document(user.id, stat['file'])
    else:
        bot.send_message(user.id, MESSAGES['no_data'])


def dialog_mon_day(par_func_name, parent_func, stat_func, *args, **kwargs):
    ASK_MONTH = 1
    ASK_DAY = 2
    DAY_SAVE = 3
    ASK_STAT = 4

    message = kwargs['message'] if not args else args[0]
    user = get_user(message)
    top_stack = user.get_cmd_stack()
    cmd_name = top_stack['cmd_name'] if top_stack else None
    if not user.town:
        user.cmd_stack = (par_func_name, parent_func,
                          {'message': message, 'exec_lvl': ASK_MONTH},
                          'город')
        settown(message, user)
    elif cmd_name != par_func_name or (
            top_stack['data'].get('exec_lvl') == ASK_MONTH):
        if cmd_name == par_func_name:
            user.cmd_stack_pop()
        user.cmd_stack = (
            par_func_name, parent_func,
            {'message': message, 'exec_lvl': ASK_DAY, 'text': ''})
        keyboard = make_month_keys()
        bot.send_message(user.id, MESSAGES['mess_decade'],
                         reply_markup=keyboard)

    elif top_stack['data'].get('exec_lvl') == ASK_DAY:
        if args:
            return bot.send_message(user.id, MESSAGES['mess_decade_month'])
        text = top_stack['data']['text']
        if text == '':
            keyboard = make_month_keys()
            return bot.send_message(user.id, MESSAGES['mess_decade'],
                                    reply_markup=keyboard)
        try:
            top_stack['data']['month'] = int(text)
        except Exception:
            top_stack = user.cmd_stack_pop()
            top_stack['data']['text'] = ''
            user.cmd_stack = top_stack
            return
        else:
            user.cmd_stack_pop()
            top_stack['data']['exec_lvl'] = DAY_SAVE
            top_stack['data']['text'] = ''
            user.cmd_stack = top_stack
            keyboard = make_day_keys(month=top_stack['data']['month'],)
            return bot.send_message(user.id, MESSAGES['mess_get_day'],
                                    reply_markup=keyboard)

    elif top_stack['data'].get('exec_lvl') == DAY_SAVE:
        if args:
            return bot.send_message(user.id, MESSAGES['mess_decade_day'])
        text = top_stack['data']['text']
        if text == 'chg_month':
            user.cmd_stack_pop()
            top_stack['data']['exec_lvl'] = ASK_MONTH
            user.cmd_stack = top_stack
            try_exec_stack(user)
        elif text == '':
            keyboard = make_day_keys(top_stack['data']['month'])
            return bot.send_message(user.id, MESSAGES['mess_decade'],
                                    reply_markup=keyboard)
        try:
            day = int(text)
        except Exception:
            top_stack = user.cmd_stack_pop()
            top_stack['data']['text'] = ''
            user.cmd_stack = top_stack
            return
        else:
            top_stack = user.cmd_stack_pop()
            top_stack['data']['day'] = day
            top_stack['data']['exec_lvl'] = ASK_STAT
            top_stack['data']['text'] = ''
            user.cmd_stack = top_stack
            keyboard = make_pass_keys()
            return bot.send_message(user.id, MESSAGES['mess_period'],
                                    reply_markup=keyboard)

    elif top_stack['data'].get('exec_lvl') == ASK_STAT:
        if args:
            return bot.send_message(user.id, MESSAGES['mess_period'])
        text = top_stack['data']['text']
        period = 0
        if text == '':
            pass
        elif text != 'pass':
            try:
                period = int(text)
            except Exception:
                top_stack = user.cmd_stack_pop()
                top_stack['data']['text'] = ''
                user.cmd_stack = top_stack
                return

        month = top_stack['data']['month']
        day = top_stack['data']['day']
        storage = kwargs.get('storage')
        params = {'town_id': user.town, 'town_name': user.town_name,
                  'day': day, 'month': month, 'period': period, 'csv': True,
                  'storage': storage}
        stat_transm(user, stat_func, params)
        user.cmd_stack_pop()
        try_exec_stack(user)


@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    user = get_user(message)
    keyboard = make_base_kbd()
    mess = MESSAGES['welcome']
    if 'help' in message.text:
        mess = ABOUT
    bot.send_message(user.id, mess, reply_markup=keyboard, )


@bot.message_handler(commands=['подсказка'])
def about(message):
    user = get_user(message)
    bot.send_message(user.id, ABOUT)


@bot.message_handler(commands=['о_дате'])
def date(message):
    user = get_user(message)
    bot.send_message(user.id, MESSAGES['mess_get_date'])


@bot.message_handler(commands=['отменить_все'])
def cancel_all(message):
    user = get_user(message)
    user.clear_stack()
    bot.send_message(user.id, MESSAGES['mess_clear'])


@bot.message_handler(commands=['город'])
def settown(message, user=None, **kwargs):
    _NAME = 'город'
    if not user:
        user = get_user(message)
    last_comm = user.get_cmd_stack()
    if not last_comm or last_comm['cmd_name'] != _NAME:
        user.cmd_stack = (_NAME, settown, {'message': message})
    bot.send_message(user.id, MESSAGES['settown'],
                     reply_markup=make_cancel_keys())


def get_day_info(message, year: int, month: int,
                 day: int, name: str = '', *args, **kwargs):
    _NAME = 'по_дате'
    name = _NAME if name == '' else name
    user = get_user(message)
    last_comm = user.get_cmd_stack()
    if not last_comm or last_comm['cmd_name'] != name:
        params = {'message': message, 'year': year, 'month': month,
                  'day': day, 'name': name}
        user.cmd_stack = (name, get_day_info, params)

    if user.town:
        stat = get_month_stat(user.town, user.town_name, year, month)
        data = stat.daystat(day, pretty=True, as_pic=True)
        if data:
            bot.send_photo(user.id, photo=data)
        else:
            bot.send_message(user.id, MESSAGES['no_data'])
        user.cmd_stack_pop()
        try_exec_stack(user)
    else:
        next = 'город'
        up_stack = user.cmd_stack_pop()
        up_stack['data']['calling'] = next
        user.cmd_stack = up_stack
        settown(message, user)


def func_select(func_id: int, params: dict, **kwargs):
    _NAME = 'команда'
    funcs = {1: get_day_info, 7: stat_week_before, 10: day_for_years}
    user = get_user(params['message'])
    if not funcs.get(func_id):
        return bot.send_message(
            user.id,
            MESSAGES['mess_unknown_comm'].format(func_id))
    if not user.town:
        next = 'город'
        user.cmd_stack = (
            _NAME, func_select, {'params': params, 'func_id': func_id},
            next)
        settown(params['message'], user)
    else:
        func = funcs[func_id]
        if func_id == 1:
            up_stack = user.get_cmd_stack()
            if up_stack and up_stack['cmd_name'] == _NAME:
                user.cmd_stack_pop()
                up_stack['cmd_name'] = 'по_дате'
                user.cmd_stack = up_stack
            return func(**params)
        params.update({
            'csv': True,
            'storage': weather_stat,
            'town_id': user.town,
            'town_name': user.town_name})
        stat_transm(user, funcs[func_id], params)
        user.cmd_stack_pop()


@bot.message_handler(commands=['год_назад'])
def get_year_ago(message):
    _NAME = MESSAGES['but_year_ago']
    now = datetime.now()
    day = int(now.strftime('%d'))
    month = int(now.strftime('%m'))
    year = int(now.strftime('%Y')) - 1
    get_day_info(message, year, month, day, _NAME)


@bot.message_handler(commands=['неделя_до', '7'])
def get_week(*args, **kwargs):
    _NAME = 'неделя_до'
    kwargs['storage'] = weather_stat
    dialog_mon_day(_NAME, get_week, stat_week_before, *args, **kwargs)


@bot.message_handler(commands=['десятилетие', '10'])
def get_decade(*args, **kwargs):
    _NAME = 'десятилетие'
    kwargs['storage'] = weather_stat
    dialog_mon_day(_NAME, get_decade, day_for_years, *args, **kwargs)


@bot.message_handler(content_types=["text"])
def auditor(message):
    user = get_user(message)
    last_command = user.cmd_stack_pop()
    if last_command and last_command.get('cmd_name'):
        if last_command['cmd_name'] == 'город':
            kwargs = {}
            town_id = towns.get_id(message.text)
            if town_id:
                user.town = town_id
                user.town_name = message.text.capitalize()
                mess = MESSAGES['town_finded']
                bot.send_message(user.id, mess, **kwargs)
                bot.send_chat_action(user.id, 'typing', 10)
                try_exec_stack(user)

            else:
                mess = MESSAGES['town_nothing']
                user.cmd_stack = last_command
                kwargs = {'reply_markup': make_cancel_keys()}
                bot.send_message(user.id, mess, **kwargs)
        else:
            if last_command and last_command['cmd']:
                last_command['data']['text'] = message.text
            user.cmd_stack = last_command
            try_exec_stack(user)
    else:
        values = comm_from_text(message.text)
        if values:
            params = values[1]
            params['message'] = message
            func_select(values[0], params)


@bot.callback_query_handler(func=lambda call: True, )
def inline_keys_exec(call):
    user = get_user(call.message)
    if call.data == 'cancel':
        up_stack = user.cmd_stack_pop()
        if not up_stack or not up_stack['cmd_name']:
            return
        all_comm = [up_stack['cmd_name'], ]
        while up_stack:
            cmd = up_stack['cmd_name']
            prev = user.get_cmd_stack()
            if not prev or cmd != prev['calling']:
                break
            user.cmd_stack_pop()
            all_comm.append(prev['cmd_name'])
        out = ', '.join(all_comm)
        bot.send_message(
            user.id,
            MESSAGES['cancel_mess'].format(out))
        try_exec_stack(user)
    else:
        up_stack = user.get_cmd_stack()
        if up_stack and up_stack['cmd'] and up_stack['cmd_name']:
            up_stack['data']['text'] = call.data
            user.cmd_stack_pop()
            user.cmd_stack = up_stack
        try_exec_stack(user)


bot.polling(non_stop=True)
