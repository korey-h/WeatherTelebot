import prettytable as pt
import re
import requests

from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw


def html_parser(html_text: str) -> dict:
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
    for params in params_list:
        town_id = params['town_id']
        month = params['month']
        year = params['year']
        url = site + pattern.format(town_id, month, year)
        r = session.get(url, headers=headers)
        if r.status_code == 200:
            mark = (town_id, year, month)
            html_text = r.content.decode('utf-8')
            to_save = parser_func(html_text)
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
                 data: dict, town_name: str = None):
        self.town_id = town_id
        self.year = year
        self.month = month if month <= 12 else 12
        self.mark = (town_id, year, month)
        self.time_stamp = datetime.now()
        self._data = data.copy()
        self.town_name = town_name.capitalize() if town_name else ''

    @property
    def month_name(self):
        return self.MONTHS[self.month]

    @property
    def stat(self):
        return self._data

    @property
    def need_upd(self):
        now = datetime.now()
        if self._data == {} or (
            (now - self.time_stamp > self.timeout) and
                now.strftime('%Y') == self.time_stamp.strftime('%Y')):
            return True
        else:
            return False

    def update(self, data: dict):
        self._data = data.copy()
        self.time_stamp = datetime.now()

    def __make_table(self, data):
        table = pt.PrettyTable(self.COLNAMES, )
        table.title = f'{self.MONTHS[self.month]} {self.year}г.' \
                      f' {self.town_name}'
        for row in data:
            table.add_row(row)
        return table.get_string()

    @staticmethod
    def _text_to_image(text: str, font_sz=14):
        rows_am = text.count('\n')
        simb_am = text.find('\n')
        im_width = int((20 + simb_am * font_sz * 0.56) // 1)
        im_height = 15 + (font_sz + 1) * rows_am
        im = Image.new('RGB', (im_width, im_height), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        font = ImageFont.truetype('cour.ttf', font_sz)
        dr.text((10, 5), text, font=font, fill='#000000')
        return im

    def daystat(self, day: int, pretty: bool = False, as_pic: bool = False):
        row = self.stat.get(str(day))
        if pretty:
            row = self.__make_table([row, ])
            if as_pic:
                row = self._text_to_image(row)
        return row


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
        r = requests.get(url, headers=self.headers)
        if r.status_code == 200:
            return r.content.decode('utf-8')

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


def day_for_years(town_id: int, town_name: str,
                  month: int, day: int, period: int = 10) -> str:

    def prep_stat(stat: list, columns: int):
        if not stat:
            return ['' for x in range(columns)]
        return stat + ['' for x in range(columns - len(stat))]

    year_now = int(datetime.now().strftime('%Y'))
    year_bf = year_now - period + 1
    params_list = [
        {'town_id': town_id,
         'month': month,
         'year': y} for y in range(year_bf, year_now + 1)]
    data = collect_stat(params_list, html_parser, container=MonthStat)
    if not data:
        return

    first_column = ('Мин', 'Ср', 'Макс', 'Откл.', 'Осадки, мм')
    col_names = [str(y) for y in range(year_bf, year_now + 1)]
    table = pt.PrettyTable()
    month_name = list(data.values())[0].month_name
    table.title = f'{day} {month_name} за период {year_bf}-' \
                  f'{year_now}гг. {town_name}'

    table.add_column('', first_column)
    for num, mark in enumerate(data):
        stat = data[mark].daystat(day)
        if not stat:
            return None
        lines = prep_stat(list(stat), len(first_column) + 1)
        table.add_column(col_names[num], lines[1:])
    return table.get_string()
