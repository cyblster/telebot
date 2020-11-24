import os
import requests
import telebot_calendar as tc

from telebot import TeleBot, types
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pytz import timezone
from json import dumps, loads

URL = "https://lk.ugatu.su/raspisanie/"
page = requests.get(URL)
page_cookies = page.cookies
page_headers = {"Referer": URL}
page_soup = BeautifulSoup(page.text, "lxml")


TOKEN = os.environ.get("TOKEN")
TIMEZONE = timezone("Asia/Yekaterinburg")

WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
SEM = "14"

GROUPS = {group.get_text():group.attrs["value"] for group in page_soup.find(id="id_group").find_all()[1:]}

START_MESSAGE = "@{}, для дальнейшей работы напиши, пожалуйста, имя своей группы. Можешь сменить её в любой момент, написав имя группы ещё раз."
GROUP_UPDATE_MESSAGE = "Группа изменена на *{}*"
NOGROUP_MESSAGE = "Для начала напиши, пожалуйста, имя своей группы."
NOSCHEDULE_MESSAGE = "Расписание отсутствует"
DATE_MESSAGE = "Пожалуйста, выбери дату"
OUTDATE_MESSAGE = "Выбрана неверная дата."
RESULT_DATE_MESSAGE = "*[{}]\n{} - я учебная неделя\n{} {} ({})*\n\n{}"
RESULT_EXAMS_MESSAGE = "*[{}]\n{}\n{}*\n\n{}"

KEYBOARD = types.ReplyKeyboardMarkup()
KEYBOARD.row("Сегодня", "Завтра")
KEYBOARD.row("Понедельник", "Вторник", "Среда")
KEYBOARD.row("Четверг", "Пятница", "Суббота")
KEYBOARD.row("Дата", "Экзамены")

CALENDAR = tc.CallbackData("calendar", "action", "year", "month", "day")

database = {}
with open("database.txt", "r") as file:
    try:
        database = loads(file.read())
    except:
        pass

bot = TeleBot(TOKEN)

def get_schedule_by_date(date, group):
    week = ((date - datetime(2020, 9, 1, tzinfo=TIMEZONE) + timedelta(datetime(2020, 9, 1, tzinfo=TIMEZONE).weekday())).days) // 7 + 1
    weekday, day, month = WEEKDAYS[date.weekday()].capitalize(), date.strftime("%d"), MONTHS[date.month - 1].capitalize()

    if  week > 20 or week < -1:
        return OUTDATE_MESSAGE

    page_data = {"csrfmiddlewaretoken": page_cookies["csrftoken"],
                "faculty": "",
                "klass": "",
                "group": group[0],
                "ScheduleType": "На дату",
                "week": "",
                "date": date.strftime('%d.%m.%Y'),
                "sem": "",
                "view": "ПОКАЗАТЬ"}

    post_page = requests.post(URL, cookies=page_cookies, headers=page_headers, data=page_data)
    post_page_soup = BeautifulSoup(post_page.text, "lxml")

    if post_page_soup.tbody == None:
        return RESULT_DATE_MESSAGE.format(group[1], week, weekday, day, month, NOSCHEDULE_MESSAGE)

    time = [time.get_text() for time in post_page_soup.tbody.find_all(class_="font-time")]
    subjects = ["\n".join(el[:4] + [" "] + el[4:]).strip(" ").strip("\n") for el in [el.split("\n") for el in [tr.find_all("td")[1].get_text(separator="\n") for tr in post_page_soup.tbody.find_all("tr")[1:]]]]
    
    schedule = "\n".join([f"*[{index + 1} пара] ({time[index]}):*\n{subjects[index]}\n" for index in range(len(subjects)) if subjects[index]])
    
    return RESULT_DATE_MESSAGE.format(group[1], week, day, month, weekday, schedule)

def get_schedule_exams(group):
    page_data = {"csrfmiddlewaretoken": page_cookies["csrftoken"],
                "faculty": "",
                "klass": "",
                "group": group[0],
                "ScheduleType": "Экзамены",
                "week": "",
                "date": "",
                "sem": SEM,
                "view": "ПОКАЗАТЬ"}
    
    post_page = requests.post(URL, cookies=page_cookies, headers=page_headers, data=page_data)
    post_page_soup = BeautifulSoup(post_page.text, "lxml")

    sem = post_page_soup.find(id="SemestrSchedule").find(value=SEM).get_text()

    if post_page_soup.tbody == None:
        return RESULT_EXAMS_MESSAGE.format(group[1], "Экзамены", sem, NOSCHEDULE_MESSAGE)

    result = [el.split("\n") for el in [tr.get_text(separator = "\n") for tr in post_page_soup.tbody.find_all("tr")[1:] if "----" not in [td.get_text(separator = "\n") for td in tr.find_all("td")]]]
    times, dates, subjects, cafs, types, teachers = list(map(list, zip(*result)))

    result = "".join([f"*{dates[index]}\n[{types[index]}] ({times[index]}):*\n{subjects[index]}\n{cafs[index]}\n{teachers[index]}\n\n" for index in range(len(date))])
    
    return RESULT_EXAMS_MESSAGE.format(group[1], "Экзамены", sem, result)

@bot.callback_query_handler(func=lambda call: call.data.startswith(CALENDAR.prefix))
def callback_inline(call: tc.CallbackQuery):
    name, action, year, month, day = call.data.split(CALENDAR.sep)
    date = tc.calendar_query_handler(bot=bot, call=call, name=name, action=action, year=year, month=month, day=day)
    if action == "DAY":
        date = datetime(date.year, date.month, date.day, tzinfo=TIMEZONE)
        bot.send_message(call.message.chat.id, get_schedule_by_date(date, database[f"{call.from_user.id}"]), parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def message_start(message):
    bot.send_message(message.chat.id, START_MESSAGE.format(message.from_user.username), reply_markup=KEYBOARD, parse_mode="Markdown")

@bot.message_handler(content_types=["text"])
def message_any(message):
    print(f"ID: {message.from_user.id}, USERNAME: {message.from_user.username}, FNAME: {message.from_user.first_name}, MESSAGE: {message.text}")
    if message.text.upper() in GROUPS:
        database.update({f"{message.from_user.id}": [GROUPS[message.text.upper()], message.text.upper()]})
        with open("database.txt", "w") as file:
            file.write(dumps(database))
        bot.send_message(message.chat.id, GROUP_UPDATE_MESSAGE.format(database[f"{message.from_user.id}"][1]), parse_mode="Markdown")
    else:
        if f"{message.from_user.id}" in database:
            date_now = datetime.now(tz=TIMEZONE)
            if message.text.lower() in WEEKDAYS:
                weekday = WEEKDAYS.index(message.text.lower())
                if date_now.weekday() >= weekday:
                    weekday += 7
                date = date_now + timedelta(weekday - date_now.weekday())
                bot.send_message(message.chat.id, get_schedule_by_date(date, database[f"{message.from_user.id}"]), parse_mode="Markdown")
            elif message.text.lower() == "сегодня":
                date = date_now + timedelta(0)
                bot.send_message(message.chat.id, get_schedule_by_date(date, database[f"{message.from_user.id}"]), parse_mode="Markdown")
            elif message.text.lower() == "завтра":
                date = date_now + timedelta(1)
                bot.send_message(message.chat.id, get_schedule_by_date(date, database[f"{message.from_user.id}"]), parse_mode="Markdown")
            elif message.text.lower() == "дата":
                calendar = tc.create_calendar(name=CALENDAR.prefix, year=date_now.year, month=date_now.month)
                bot.send_message(message.chat.id, DATE_MESSAGE, reply_markup=calendar, parse_mode="Markdown")
            elif message.text.lower() == "экзамены":
                bot.send_message(message.chat.id, get_schedule_exams(database[f"{message.from_user.id}"]), parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, NOGROUP_MESSAGE, parse_mode="Markdown")

bot.polling()