#!/usr/bin/env python3

import random
import re
import os
import pickle
import schedule
import threading

import time
from requests import get
from json import loads
import telebot

if os.path.exists("vk.token"):
    with open("vk.token") as vk:
        VK_TOKEN = vk.read().strip()
else:
    print("No vk token (resender)")
    exit(1)
if os.path.exists("telegram.token"):
    with open("telegram.token") as tele:
        TELE_TOKEN = tele.read().strip()
else:
    print("No telegram token (resender)")
    exit(1)
if os.path.exists("posts.dump"):
    with open("posts.dump", mode="rb") as dump:
        posts = pickle.load(dump)
else:
    posts = {}
if os.path.exists("groups.dump"):
    with open("groups.dump", mode="rb") as dump:
        groups = pickle.load(dump)
else:
    groups = {}

bot = telebot.TeleBot(TELE_TOKEN)

def replace_names(post):
    r = re.compile("\[id[0-9]+\|[a-zA-Zа-яА-Я0-9]+\s[a-zA-Zа-яА-Я0-9]+\]")
    matches = r.findall(post["text"])
    for m in matches:
        name = m[m.find("|") + 1:-1]
        post["text"] = post["text"].replace(m, name)


def get_latest_post(group_name):
    posts_resp = loads(get(f"https://api.vk.com/method/wall.get?access_token={VK_TOKEN}&domain={group_name}&count=10").content)
    print(posts_resp)
    print(group_name)
    posts_loc = sorted(posts_resp['response'][1:], key=lambda post: post['id'])
    latest = posts[group_name][-1]["id"] if len(posts[group_name]) > 0 else 0
    posts_with_br = [x for x in posts_loc if x['id'] > latest and check_if_writing(x['text'])]
    r = re.compile(r"\[id[0-9]+\|[a-zA-Zа-яА-Я0-9]+\s[a-zA-Zа-яА-Я0-9]+\]")
    for post in posts_with_br:
        post["text"] = post["text"].replace("<br>", '\n')
        matches = r.findall(post["text"])
        for m in matches:
            name = m[m.find("|") + 1:-1]
            post["text"] = post["text"].replace(m, name)
    posts[group_name] += posts_with_br
    with open("posts.dump", mode='wb') as dump:
        pickle.dump(posts, dump)


def check_if_writing(text):
    tags = ["#poetry", "#стихи", "#story", "#проза"]
    for tag in tags:
        if tag in text:
            return tag
    return ""


def check_all():
    for group in posts:
        get_latest_post(group)
        time.sleep(1)


def send_to_telegram():
    print(111)
    for chan in groups:
        candidates = []
        for group in groups[chan]:
            if group in posts:
                candidates.append(random.choice(posts[group]))
        post = random.choice(candidates)
        print(post)
        for list in posts.values():
            if post in list:
                list.remove(post)
                break
        text = post["text"] + f"\n\nhttps://vk.com/wall{post['to_id']}_{post['id']}"
        messages = split_closest_to(text, "\n", 3000)
        for message in messages:
            bot.send_message(chan, message)
        if "attachments" in post:
            for img in [att["photo"] for att in post["attachments"] if att["type"] == "photo"]:
                imgfile = get(img["src_big"]).content
                bot.send_photo(chan, imgfile)
        with open("posts.dump", mode='wb') as dump:
            pickle.dump(posts, dump)


def split_closest_to(string, sep, length):
    lines = string.split(sep)
    cur_line = ""
    res = []
    for line in lines:
        if len(cur_line) + len(line) > length:
            res.append(cur_line)
            cur_line = line
        else:
            cur_line += sep + line
    res.append(cur_line) if cur_line != "" else False
    return res


@bot.message_handler(content_types=["text"])
def response(m):
    bot.send_message(m.chat.id, "Sorry, now for channel posting purposes only")


def pend():
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    schedule.every().day.at("9:00").do(check_all)
    schedule.every().sunday.at("10:00").do(send_to_telegram)
    t = threading.Thread(target=pend)
    t.daemon = True
    t.start()
    bot.polling(none_stop=True)

