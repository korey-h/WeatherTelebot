import prettytable as pt
import re
import requests
import time

from datetime import datetime, timedelta
from io import StringIO
from PIL import Image, ImageFont, ImageDraw
from typing import Tuple


def html_parser(html_text: str) -> dict:
    '''Ищет в html-тексте данные по шаблону.
    Найденное возвращает в виде словаря
    {'A': ('A', 'B', 'C', 'D', 'E', 'F'), }'''

    data = {}
    COLUMNS = 6

    def get_row(taged_row: str):
        row = re.sub(r'<td[^>]*>', '', taged_row)
        row = re.sub(r'</td>', ';', row)
        row = re.sub(r'\s*</?tr>\s*', '', row).rstrip(';')
        return row.split(';')

    def get_table_area(page_text: str):
        page_text = page_text.replace('\n', '')
        l_verge = r'<div[^>]*>\s*<table>'
        r_verge = r'</table>'
        start = re.search(l_verge, page_text).end()
        pattern = re.compile(r_verge)
        end = pattern.search(page_text, start).start()
        return page_text[start:end]

    if not html_text:
        return None
    table_area = get_table_area(html_text).replace('\n', '')
    cursor = 0
    size = len(table_area)
    while cursor < size:
        pattern = re.compile(r'<tr.*?</tr>')
        finded_row = pattern.search(table_area, cursor)
        if not finded_row:
            break
        cursor = finded_row.end()
        row = get_row(finded_row[0])
        try:
            int(row[0])
        except Exception:
            continue
        data.update({row[0]: tuple(row[:COLUMNS])})
    return data


def collect_stat(params_list: list, parser_func,
                 container=None) -> dict:
    ''' params_list - список словарей содержания
    {town_id: int, year: int, month: int, town_name: str} '''

    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:106.0)\
            Gecko/20100101 Firefox/106.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
            image/avif,image/webp,*/*;q=0.8'
        }
    site = 'http://www.pogodaiklimat.ru'
    pattern = '/monitor.php?id={}&month={}&year={}'
    session = requests.Session()
    data = {}
    null_day = ['-' for _ in range(5)]
    null_stat = {str(d): [str(d)] + null_day for d in range(1, 32)}

    for params in params_list:
        town_id = params['town_id']
        month = params['month']
        year = params['year']
        url = site + pattern.format(town_id, month, year)
        r = session.get(url, headers=headers)
        to_save = null_stat
        params['bad_data'] = True
        if r.status_code == 200:
            mark = (town_id, year, month)
            html_text = r.content.decode('utf-8')
            try:
                to_save = parser_func(html_text)
            except Exception:
                pass
            else:
                params['bad_data'] = False

        if container:
            data[mark] = container(data=to_save, **params)
        else:
            data[mark] = to_save
    return data


class MonthStat:
    MONTHS = {
        1: 'январь', 2: 'февраль', 3: 'март',
        4: 'апрель', 5: 'май', 6: 'июнь',
        7: 'июль', 8: 'август', 9: 'сентябрь',
        10: 'октябрь', 11: 'ноябрь', 12: 'декабрь',
    }
    COLNAMES = ('Дата', 'Мин', 'Ср', 'Макс',
                'Откл.', 'Осадки, мм')

    timeout = timedelta(hours=1)

    def __init__(self, town_id: int, year: int, month: int,
                 data: dict, town_name: str = None,
                 bad_data: bool = True):
        self.town_id = town_id
        self.year = year
        self.month = month if month <= 12 else 12
        self.mark = (town_id, year, month)
        self.time_stamp = datetime.now()
        self._data = data.copy()
        self._bad_data = bad_data
        self.town_name = town_name.capitalize() if town_name else ''
        self.lenth = self._lenth(self.month, self.year)

    @staticmethod
    def _lenth(month: int, year: int) -> int:
        if month in (4, 6, 9, 11):
            return 30
        elif month == 2:
            if not year % 4 and (year % 100 and year % 400 or
                                 not year % 100 and not year % 400):
                return 29
            return 28
        return 31

    @property
    def month_name(self):
        return self.MONTHS[self.month]

    @property
    def stat(self):
        return self._data

    @property
    def need_upd(self):
        now = datetime.now()
        if self._bad_data:
            return True
        if self._data == {} or (
            (now - self.time_stamp > self.timeout) and
                now.strftime('%Y') == self.time_stamp.strftime('%Y')):
            return True
        else:
            return False

    def update(self, data: dict):
        self._data = data.copy()
        self.time_stamp = datetime.now()
        self._bad_data = False

    def __make_table(self, data):
        table = pt.PrettyTable(self.COLNAMES, )
        table.title = f'{self.MONTHS[self.month]} {self.year}г.' \
                      f' {self.town_name}'
        for row in data:
            table.add_row(row)
        return table.get_string()

    @staticmethod
    def _text_to_image(text: str, font_sz=16, width_limit=10000):
        X, Y = 10, 5
        chr_width = {10: 6, 12: 7, 14: 8, 16: 10}
        font_width = chr_width[font_sz] if font_sz in chr_width else 10

        rows_am = text.count('\n')
        simb_in_row = text.find('\n')
        im_width = X * 2 + simb_in_row * font_width
        im_height = Y * 2 + (font_sz + 2) * (rows_am + 1)
        if im_width + im_height > width_limit or im_width > 10 * im_height:
            return None
        im = Image.new('RGB', (im_width, im_height), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        font = ImageFont.truetype('cour.ttf', font_sz)
        dr.text((X, Y), text, font=font, fill='#000000')
        return im

    def daystat(self, day: int, pretty: bool = False, as_pic: bool = False):
        day = self.lenth if day > self.lenth else day
        row = self.stat.get(str(day))
        row = list(row) + ['-' for x in range(len(self.COLNAMES) - len(row))]
        if pretty:
            row = self.__make_table([row, ])
            if as_pic:
                row = self._text_to_image(row)
        return row

    @property
    def stat_pretty(self) -> str:
        return self.__make_table(self._data.values())


class Towns:
    site = 'http://www.pogodaiklimat.ru'
    params = '/monitor.php'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:81.0)"
        }
    timeout = timedelta(days=1)

    def __init__(self):
        self.time_stamp = datetime.now()
        self._data = {}
        self.__make_data()

    def _get_html(self):
        url = self.site + self.params
        max_req = 24
        timeout = 10
        while max_req:
            try:
                r = requests.get(url, headers=self.headers)
            except Exception as e:
                print(e)
            else:
                if r.status_code == 200:
                    return r.content.decode('utf-8')
            finally:
                max_req -= 1
                time.sleep(timeout)

    @staticmethod
    def __get_row(taget_row: str):
        cursor = 0
        id_patn = re.compile(r'id=\d+')
        finded = id_patn.search(taget_row, cursor)
        if not finded:
            return ()
        town_id = int(finded[0][3:])
        cursor = finded.end()
        town_patn = re.compile(r'\b\w+\b')
        finded = town_patn.search(taget_row, cursor)
        if not finded:
            return ()
        town = finded[0].lower()
        return {town: town_id}

    def __make_data(self):
        page_text = self._get_html()
        if not page_text:
            return None
        cursor = 0
        size = len(page_text)
        while cursor < size:
            pattern = re.compile(r'<li.*?href.*?</li>')
            finded_row = pattern.search(page_text, cursor)
            if not finded_row:
                break
            cursor = finded_row.end()
            row = self.__get_row(finded_row[0])
            self._data.update(row)

    def __update(self):
        now = datetime.now()
        if self._data == {} or (
            (now - self.time_stamp > self.timeout) and
                now.strftime('%Y') == self.time_stamp.strftime('%Y')):
            self.__make_data()

    def get_id(self, name: str):
        self.__update()
        return self._data.get(name.lower())


def make_csv(rows: list, col_names: list = None,
             title: str = None, f_name: str = 'info') -> StringIO:
    csv_data = '\ufeff'
    if title:
        csv_data += title + ';' + '\r\n'
    if col_names:
        csv_data += ';'.join(col_names) + '\r\n'
    for row in rows:
        raw = ';'.join(str(x) for x in row)
        csv_data += raw.replace('.', ',') + '\r\n'
    file = StringIO(csv_data)
    file.name = f_name + '.csv'
    return file


def day_for_years(town_id: int, town_name: str,
                  month: int, day: int, period: int = 10, csv=False,
                  storage: dict = None, **kwargs) -> Tuple[str, StringIO]:
    """ Возвращает таблицу в виде строки. Таблица содержит
    информация о максимальной, минимальной и средней температуре, а также
    количестве осадков для выбранной даты month, day на протяжении
    нескольких лет в выбранном периоде period"""

    def prep_stat(stat: list, columns: int):
        if not stat:
            return ['' for x in range(columns)]
        return stat + ['' for x in range(columns - len(stat))]

    period = 10 if period > 60 or period <= 0 else period
    year_now = int(datetime.now().strftime('%Y'))
    year_bf = year_now - period + 1
    params_list = []
    months = []
    for y in range(year_bf, year_now + 1):
        mark = (town_id, y, month)
        months.append(mark)
        empty = storage and (
            not storage.get(mark) or storage.get(mark).need_upd)
        if empty or not storage:
            params = {'town_id': town_id, 'month': month,
                      'town_name': town_name, 'year': y}
            params_list.append(params)

    data = collect_stat(params_list, html_parser, container=MonthStat)
    if data and storage is not None:
        storage.update(data)
    elif data and storage is None:
        storage = data
    elif not data and storage is None:
        return

    first_column = ('Мин', 'Ср', 'Макс', 'Откл', 'Осадки, мм')
    col_names = [str(y) for y in range(year_bf, year_now + 1)]
    table = pt.PrettyTable()
    m_name = storage[months[0]].month_name
    m_name = m_name + 'а' if m_name[-1] == 'т' else m_name[:-1] + 'я'
    table.title = f'{day} {m_name} за период {year_bf}-' \
                  f'{year_now}гг. {town_name}'

    table.add_column('', first_column)
    for num, mark in enumerate(months):
        stat = storage[mark].daystat(day)
        if not stat:
            return None
        lines = prep_stat(list(stat), len(first_column) + 1)
        table.add_column(col_names[num], lines[1:])
    out = {'table': table.get_string()}
    if csv:
        out['file'] = make_csv(table.rows, table.field_names, table.title,
                               f_name='day_for_years')
    return out


def stat_week_before(town_id: int, town_name: str,
                     month: int, day: int, period: int = 10, csv=False,
                     storage: dict = None, **kwargs) -> Tuple[str, StringIO]:
    """ Возвращает таблицу в виде строки. Таблица содержит
    информация о средней температуре и количестве осадков в течение
    одной недели до выбранной даты month, day (включая ее) для нескольких лет в
    выбранном периоде period"""

    year_now = int(datetime.now().strftime('%Y'))
    period = 10 if period > 60 or period <= 0 else period

    # проверка вхождения дней предыдущего месяца в неделю
    base_months = [(town_id, year_now, month), ]
    if day - 7 < 0 and month > 1:
        base_months.append((town_id, year_now, month - 1))
    elif day - 7 < 0 and month == 1:
        base_months.append((town_id, year_now - 1, 12))

    # определение месяцев, по которым собирается статистика
    params_list = []
    for i in range(0, period):
        for mon in base_months:
            mark = (mon[0], mon[1] - i, mon[2])
            empty = storage and (
                not storage.get(mark) or storage.get(mark).need_upd)
            if empty or not storage:
                param = {'town_id': mon[0], 'year': mon[1] - i,
                         'month': mon[2], 'town_name': town_name}
                params_list.append(param)

    data = collect_stat(params_list, html_parser, container=MonthStat)
    if data and storage is not None:
        storage.update(data)
    elif data and storage is None:
        storage = data
    elif not data and storage is None:
        return

    # определение дат, попавших в неделю
    week_template = []
    date = day
    days_count = 7
    for mark in base_months:
        if date < 1:
            mon = storage[mark]
            date = mon.lenth
        while date >= 1 and days_count > 0:
            week_template.append((mark, date))
            date -= 1
            days_count -= 1
    week_template.reverse()

    # подготовка оформления таблицы
    table = pt.PrettyTable()
    first_col = ['-'.join([str(m[1] - i // 2) for m in base_months[::-1]])
                 if i % 2 == 0 else ''
                 for i in range(0, period * 2)]
    second_col = ['ср.темп.' if i % 2 == 0 else 'осадки'
                  for i in range(0, period * 2)]
    table.add_column('ГОД', first_col)
    table.add_column('день/мес.', second_col)

    # заполнение таблицы данными
    for mon, date in week_template:
        field_name = f'{date}/{mon[2]}'
        column = []
        for i in range(0, period):
            mark = (mon[0], mon[1] - i, mon[2])
            stat = storage[mark].daystat(date)
            column.append(stat[2])
            column.append(stat[5])
        table.add_column(field_name, column)
    m_name = storage[base_months[0]].month_name
    m_name = m_name + 'а' if m_name[-1] == 'т' else m_name[:-1] + 'я'

    table.title = f'Статистика погоды на неделе перед {day} {m_name} ' \
                  f'за период {base_months[-1][1] - period + 1}'\
                  f'-{year_now} гг.' \
                  f' {town_name}'
    out = {'table': table.get_string()}
    if csv:
        out['file'] = make_csv(table.rows, table.field_names, table.title,
                               f_name='week_before')
    return out


def clear_date(date: list) -> list:
    ''' Принимает последовательность [день, месяц, год].
    Проверяет, чтобы день и месяц не выходили за допустимые границы.
    Возвращает подправленный список [день, месяц, год] в
    целых числах'''

    DAY = 0
    MONTH = 1
    YEAR = 2
    date = [int(d) for d in date]
    if date[MONTH] > 12:
        date[MONTH] = 12
    elif date[MONTH] < 1:
        date[MONTH] = 1

    m_len = MonthStat._lenth(date[MONTH], date[YEAR])
    if date[DAY] > m_len:
        date[DAY] = m_len
    elif date[DAY] < 1:
        date[DAY] = 1
    return date


def comm_from_text(text: str):
    func_id = 1
    period = 0

    date_pattern = re.compile(r'\d{1,2}[-_\/\.]\d{1,2}[-_\/\.]\d\d\d\d')
    num_patt = re.compile(r'\s*?\d{1,2}\s*?')
    res = date_pattern.search(text)
    if not res:
        return
    raw_date = res[0]
    for sep in ('_/.'):
        raw_date = raw_date.replace(sep, '-')
    date = raw_date.split('-')
    date = clear_date(date)
    res = num_patt.search(text, res.end())
    func_id = int(res[0].strip()) if res else func_id
    if res:
        res = num_patt.search(text, res.end())
        period = int(res[0].strip()) if res else period

    params = {'day': date[0], 'month': date[1],
              'year': date[2], 'period': period}
    return (func_id, params)


def words_finder(text: str, keywords: list) -> bool:
    for word in keywords:
        if word in text:
            return True
    return False


def ask_help(text: str) -> bool:
    keywords = ['меню', 'помощ', 'команд', 'можеш', 'умееш']
    return words_finder(text, keywords)


def forecast(text: str) -> bool:
    keywords = ['завтра', 'через', 'прогноз', 'будущ']
    return words_finder(text, keywords)
