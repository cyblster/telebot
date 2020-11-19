# -*- coding: utf-8 -*-

import os
import telebot
import requests
import json

from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://lk.ugatu.su/raspisanie/"

TOKEN = os.environ.get("TOKEN")

keywords = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье", "сегодня", "завтра", "послезавтра", "неделя"]

database = {}
with open("database.txt", "r") as file:
    try:
        database = json.loads(file.read())
    except:
        pass

getResponse = requests.get(URL)
getResponseSoup = BeautifulSoup(getResponse.text, "lxml")



bot = telebot.TeleBot(TOKEN)

def pop_duplicates(keys):
    temp = []
    for key in keys:
        if key not in temp:
            temp.append(key)
    return temp

def send_message(chat_id, group_name, date, time, subjects):
    subjects = ["\n".join(el[:4] + [" "] + el[4:]).strip(" ").strip("\n") for el in [el.split("\n") for el in subjects]]
    botMsg = "\n".join([f"*[{index + 1} пара] ({time[index]}):*\n{subjects[index]}\n" for index in range(len(subjects)) if subjects[index]])
    if botMsg:
        bot.send_message(chat_id, f"*[{group_name}]*\n*{date}*\n\n{botMsg}", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"*[{group_name}]*\n*{date}*\n\nРасписание отсутствует", parse_mode="Markdown")

@bot.message_handler(["start"])
def help_message(message):
    bot.send_message(message.chat.id, "Список команд\n===\n" +
                     "*/гр* _[группа]_\nДобавить/изменить группу\n=\n" +
                     "*/расп* _[день]/завтра/сегодня/неделя_\nРасписание на день/неделю", parse_mode="Markdown")

@bot.message_handler(["гр"])
def group_message(message):
    message_text = message.text[4:].lower()
    user_id = str(message.from_user.id)
    if message_text:
        group_name = getResponseSoup.find(string = message_text.upper())
        if group_name:
            database.update({f"{user_id}": group_name})
            with open("database.txt", "w") as file:
                    file.write(json.dumps(database))
            bot.send_message(message.chat.id, f"Группа изменена на *{group_name}*", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"Группа *{message_text.upper()}* не найдена", parse_mode="Markdown")
    else:
        if user_id in database:
            bot.send_message(message.chat.id, f"Ваша группа *{database[str(user_id)]}*", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"Ваша группа не установлена\n*/гр* _[группа]_\nДобавить/изменить группу", parse_mode="Markdown")
            
@bot.message_handler(["расп"])
def rasp_message(message):
    message_text = pop_duplicates(message.text[6:].lower().split())
    user_id = str(message.from_user.id)
    
    if user_id in database:
        getResponse = requests.get(URL)
        getResponseSoup = BeautifulSoup(getResponse.text, "lxml")
        
        cookies = getResponse.cookies
        headers = {"Referer": URL}
        data = {"csrfmiddlewaretoken": getResponseSoup.form.input["value"],
                "faculty": "",
                "klass": "",
                "group": getResponseSoup.find(string = database[user_id]).parent["value"],
                "ScheduleType": "За неделю",
                "week": getResponseSoup.p.font.text,
                "date": "",
                "sem": "14",
                "view": "ПОКАЗАТЬ"}        
        
        postResponse = requests.post(URL, data=data, cookies=cookies, headers=headers)
        postResponseSoup = BeautifulSoup(postResponse.text, "lxml") 
        
        chat_id = message.chat.id
        group_name = database[user_id]  
        time = [td.get_text(separator = "\n").split("\n")[1] for td in [tr.find_all("td")[0] for tr in postResponseSoup.tbody.find_all("tr")]]
        if message_text:
            for key in message_text:
                if key in keywords:
                    if 0 < keywords.index(key) + 1 < 7:
                        date = postResponseSoup.thead.find_all("th")[keywords.index(key) + 1].get_text(separator = ", ")
                        subjects = [td.get_text(separator = "\n") for td in [tr.find_all("td")[keywords.index(key) + 1] for tr in postResponseSoup.tbody.find_all("tr")]]
                        
                        send_message(chat_id, group_name, date, time, subjects)
                    elif key == "сегодня" and datetime.now().weekday() != 6:
                        date = postResponseSoup.thead.find_all("th")[datetime.now().weekday() + 1].get_text(separator = ", ")
                        subjects = [td.get_text(separator = "\n") for td in [tr.find_all("td")[datetime.now().weekday() + 1] for tr in postResponseSoup.tbody.find_all("tr")]]
                        
                        send_message(chat_id, group_name, date, time, subjects)
                    elif key == "завтра" and datetime.now().weekday() != 5:
                        date = postResponseSoup.thead.find_all("th")[datetime.now().weekday() + 2].get_text(separator = ", ")
                        subjects = [td.get_text(separator = "\n") for td in [tr.find_all("td")[datetime.now().weekday() + 2] for tr in postResponseSoup.tbody.find_all("tr")]]
                        
                        send_message(chat_id, group_name, date, time, subjects)
                    elif key == "послезавтра" and datetime.now().weekday() != 4:
                        date = postResponseSoup.thead.find_all("th")[datetime.now().weekday() + 3].get_text(separator = ", ")
                        subjects = [td.get_text(separator = "\n") for td in [tr.find_all("td")[datetime.now().weekday() + 3] for tr in postResponseSoup.tbody.find_all("tr")]]
                        
                        send_message(chat_id, group_name, date, time, subjects)
                    elif key == "неделя":
                        dates = [date.get_text(separator = ", ") for date in postResponseSoup.thead.find_all("th")[1:]]
                        subjects = list(map(list, zip(*[[td.get_text(separator = "\n") for td in tr.find_all("td")[1:]] for tr in postResponseSoup.tbody.find_all("tr")])))
                        
                        for index in range(len(dates)):
                            send_message(chat_id, group_name, dates[index], time, subjects[index])
        else:
            date = postResponseSoup.thead.find_all("th")[datetime.now().weekday() + 1].get_text(separator = ", ")
            subjects = [td.get_text(separator = "\n") for td in [tr.find_all("td")[datetime.now().weekday() + 1] for tr in postResponseSoup.tbody.find_all("tr")]]
            
            send_message(chat_id, group_name, date, time, subjects)
                
    else:
        bot.send_message(message.chat.id, f"Ваша группа не установлена\n*/гр* _[группа]_\nДобавить/изменить группу", parse_mode="Markdown")
    
bot.polling()
