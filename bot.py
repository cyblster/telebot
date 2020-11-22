# -*- coding: utf-8 -*-

import os
import requests
import telebot
import telebot_calendar

from telebot_calendar import CallbackData
from telebot.types import ReplyKeyboardRemove, CallbackQuery

from bs4 import BeautifulSoup
from datetime import datetime, date
from pytz import timezone
from json import dumps, loads

URL = "https://lk.ugatu.su/raspisanie/"
TOKEN = os.environ.get("TOKEN")
TIMEZONE = timezone('Asia/Yekaterinburg')

START_MESSAGE = "@{}, для дальнейшей работы напиши, пожалуйста, имя своей группы. Можешь сменить её в любой момент, написав имя группы ещё раз."
GROUP_UPDATE_MESSAGE = "Группа изменена на *{}*"
NOGROUP_MESSAGE = "Для начала напиши, пожалуйста, имя своей группы."
NOSCHEDULE_MESSAGE = "Расписание отсутствует"
DATE_MESSAGE = "Пожалуйста, выбери дату"
OUTDATE_MESSAGE = "Выбрана неверная дата."

KEYBOARD = telebot.types.ReplyKeyboardMarkup()
KEYBOARD.row("Сегодня", "Завтра")
KEYBOARD.row("Понедельник", "Вторник", "Среда")
KEYBOARD.row("Четверг", "Пятница", "Суббота")
KEYBOARD.row("Дата")
KEYBOARD.row("Экзамены")

CALENDAR = CallbackData("calendar", "action", "year", "month", "day")

database = {}
with open("database.txt", "r") as file:
    try:
        database = loads(file.read())
    except:
        pass


bot = telebot.TeleBot(TOKEN)

client = requests.session()
page = client.get(URL)
page_cookies = page.cookies
page_headers = {"Referer": URL}
page_soup = BeautifulSoup(page.text, "lxml")

def get_schedule_by_day(day_index, group_id, type_id):
    csrftoken = page_cookies["csrftoken"]
    week = page_soup.p.font.text
    next_week_flag = 0
    if day_index <= datetime.now(tz=TIMEZONE).weekday() and type_id or day_index > 6:
        day_index %= 7
        week = f"{int(week) + 1}"
        next_week_flag = 1
    sem = "14"
    
    page_data = {"csrfmiddlewaretoken": csrftoken,
            "faculty": "",
            "klass": "",
            "group": group_id,
            "ScheduleType": "За неделю",
            "week": week,
            "date": "",
            "sem": sem,
            "view": "ПОКАЗАТЬ"}
    
    post_page = requests.post(URL, cookies=page_cookies, headers=page_headers, data=page_data)
    post_page_soup = BeautifulSoup(post_page.text, "lxml")
    
    group_name = post_page_soup.find(id="id_group").find(value=group_id).get_text()
    
    date = f"{['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][day_index]}, {int(datetime.now(tz=TIMEZONE).day) + day_index - datetime.now(tz=TIMEZONE).weekday() + 7 * next_week_flag} {['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'][int(datetime.now(tz=TIMEZONE).month) - 1]}"
    
    if post_page_soup.tbody == None or day_index == 6:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{NOSCHEDULE_MESSAGE}"
        return result
    
    time = [td.get_text(separator="\n").split("\n")[1] for td in [tr.find_all("td")[0] for tr in post_page_soup.tbody.find_all("tr")]]
    subjects = ["\n".join(el[:4] + [" "] + el[4:]).strip(" ").strip("\n") for el in [el.split("\n") for el in [td.get_text(separator = "\n") for td in [tr.find_all("td")[day_index + 1] for tr in post_page_soup.tbody.find_all("tr")]]]]
    
    result = "\n".join([f"*[{index + 1} пара] ({time[index]}):*\n{subjects[index]}\n" for index in range(len(subjects)) if subjects[index]])
    
    if result:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{result}"
    else:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{NOSCHEDULE_MESSAGE}"
    
    return result

def get_schedule_by_date(date, group_id):
    csrftoken = page_cookies["csrftoken"]
    week = f"{(int((date - datetime(2020, 9, 1)).days) + int(datetime(2020, 9, 1).day)) // 7 + 1}"
    sem = "14"
    
    page_data = {"csrfmiddlewaretoken": csrftoken,
            "faculty": "",
            "klass": "",
            "group": group_id,
            "ScheduleType": "На дату",
            "week": "",
            "date": date.strftime('%d.%m.%Y'),
            "sem": sem,
            "view": "ПОКАЗАТЬ"}
    
    post_page = requests.post(URL, cookies=page_cookies, headers=page_headers, data=page_data)
    post_page_soup = BeautifulSoup(post_page.text, "lxml")
    
    if post_page_soup.find(id="id_group") == None or int(week) < -1:
        return OUTDATE_MESSAGE
    
    group_name = post_page_soup.find(id="id_group").find(value=group_id).get_text()
    
    date = f"{['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][date.weekday()]}, {date.day} {['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'][int(date.month) - 1]}"
    
    if post_page_soup.tbody == None:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{NOSCHEDULE_MESSAGE}"
        return result
    
    time = [tr.find("td").get_text(separator="\n").split("\n")[1] for tr in post_page_soup.tbody.find_all("tr")[1:]]
    subjects = ["\n".join(el[:4] + [" "] + el[4:]).strip(" ").strip("\n") for el in [el.split("\n") for el in [tr.find_all("td")[1].get_text(separator="\n") for tr in post_page_soup.tbody.find_all("tr")[1:]]]]
    
    result = "\n".join([f"*[{index + 1} пара] ({time[index]}):*\n{subjects[index]}\n" for index in range(len(subjects)) if subjects[index]])
    
    if result:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{result}"
    else:
        result = f"*[{group_name}]\n{week} - я учебная неделя\n{date}*\n\n{NOSCHEDULE_MESSAGE}"
    
    return result

def get_exams(group_id):
    csrftoken = page_cookies["csrftoken"]
    sem = "14"
    
    page_data = {"csrfmiddlewaretoken": csrftoken,
            "faculty": "",
            "klass": "",
            "group": group_id,
            "ScheduleType": "Экзамены",
            "week": "",
            "date": "",
            "sem": sem,
            "view": "ПОКАЗАТЬ"}
    
    post_page = requests.post(URL, cookies=page_cookies, headers=page_headers, data=page_data)
    post_page_soup = BeautifulSoup(post_page.text, "lxml")
    
    group_name = post_page_soup.find(id="id_group").find(value=group_id).get_text()
    
    if post_page_soup.tbody == None:
        result = f"*[{group_name}]\nЭкзамены*\n\n{NOSCHEDULE_MESSAGE}"
        return result
    
    result = [el.split("\n") for el in [tr.get_text(separator = "\n") for tr in post_page_soup.tbody.find_all("tr")[1:] if "----" not in [td.get_text(separator = "\n") for td in tr.find_all("td")]]]
    time, date, name, caf, type, prepod = list(map(list, zip(*result)))
    
    result = "".join([f"*{date[index]}\n[{type[index]}] ({time[index]}):*\n{name[index]}\n{caf[index]}\n{prepod[index]}\n\n" for index in range(len(date))])
    
    if result:
        result = f"*[{group_name}]\nЭкзамены*\n\n{result}"
    else:
        result = f"*[{group_name}]\nЭкзамены*\n\n{NOSCHEDULE_MESSAGE}"
    
    return result

@bot.callback_query_handler(func=lambda call: call.data.startswith(CALENDAR.prefix))
def callback_inline(call: CallbackQuery):
    name, action, year, month, day = call.data.split(CALENDAR.sep)
    date = telebot_calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action, year=year, month=month, day=day)
    if action == "DAY":
            bot.send_message(call.message.chat.id, get_schedule_by_date(date, database[f"{call.from_user.id}"]), parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def handle_start(message):   
    bot.send_message(message.chat.id, START_MESSAGE.format(message.from_user.username), parse_mode="Markdown", reply_markup=KEYBOARD)

@bot.message_handler(content_types=["text"])
def handle_text(message):
    message_text = message.text.lower()
    group_name = page_soup.find(id="id_group").find(string=message_text.upper())
    if group_name:
        database.update({f"{message.from_user.id}": group_name.parent["value"]})
        with open("database.txt", "w") as file:
            file.write(dumps(database))
        bot.send_message(message.chat.id, GROUP_UPDATE_MESSAGE.format(group_name), parse_mode="Markdown")
    elif f"{message.from_user.id}" in database:
        if message_text in ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]:
            day_index = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"].index(message_text)
            bot.send_message(message.chat.id, get_schedule_by_day(day_index, database[f"{message.from_user.id}"], 1), parse_mode="Markdown") 
        elif message_text == "сегодня":
            day_index = datetime.now(tz=TIMEZONE).weekday()
            bot.send_message(message.chat.id, get_schedule_by_day(day_index, database[f"{message.from_user.id}"], 0), parse_mode="Markdown")
        elif message_text == "завтра":
            day_index = datetime.now(tz=TIMEZONE).weekday() + 1
            bot.send_message(message.chat.id, get_schedule_by_day(day_index, database[f"{message.from_user.id}"], 0), parse_mode="Markdown")     
        elif message_text == "дата":
            date_now = datetime.now(tz=TIMEZONE)
            inline_calendar = telebot_calendar.create_calendar(name=CALENDAR.prefix,
                                                               year=date_now.year,
                                                               month=date_now.month)
            bot.send_message(message.chat.id, DATE_MESSAGE, reply_markup=inline_calendar, parse_mode="Markdown")
        elif message_text == "экзамены":
            bot.send_message(message.chat.id, get_exams(database[f"{message.from_user.id}"]), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, NOGROUP_MESSAGE.format(), parse_mode="Markdown")    

if __name__ == "__main__": 
    bot.polling(none_stop=False, timeout=30)