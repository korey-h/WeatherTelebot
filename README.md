# WeatherTelebot
Бот для Telegram для получения погодной статистики с сайта
www.pogodaiklimat.ru
## Где посмотреть работу
В Telegram по имени @WeatherStoryBot .
## Что умеет:
- показывать данные о минимальной/максимальной температуре и количестве осадков для указанной даты и выбранного города в виде таблицы;
- показывать статистику за период 10 лет для недели, предшествующей введенной дате;
- получать команды с виртуальной клавиатуры и из контекста сообщения.
## Как запустить
 - установить Python 3.7 или новее, Pip;
 - установить модули, указанные в requirements.txt (pip install -r requirements.txt);
 - в папку с файлами бота добавить файл .env, внутри которого должен быть указан токен бота:
   TOKEN = 'хххххххх:ааааааааааааааааааааааааа'
   (токен запрашивается в Telegram у @BotFather при создании профиля бота);
 - в папку с файлами бота добавить файл моноширинного шрифта Courier (cour.ttf);
 - запустить файл bot.py