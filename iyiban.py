#!/usr/bin/env python3
# coding: utf-8

import os
import re
import csv
import json
import asyncio
import aiohttp
import logging
from functools import partial


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

HIT = re.compile(r'<li\sclass="courses-listing-item">.+?<a\shref="(.*?)">.+?<img\ssrc="(.*?)".+?title="(.*?)"', re.DOTALL)
JED = re.compile(r'<ul\sclass="fcw\sclearfix">.+?<li>提供学校：(.*?)<\/li>.+?<span>(\d+?)<\/span>.+?<li\s.+?>课程代码：(.*?)<\/li>', re.DOTALL)
Z = re.compile(r'<em\sid="favorites">(\d+?)<\/em>', re.DOTALL)
C = re.compile(r'<em\sid="unfavorites">(\d+?)<\/em>', re.DOTALL)
N = re.compile(r'<h1\sclass="fcw".*?">(.*?)<\/h1>', re.DOTALL)

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36'
HOST = 'http://www.iyiban.cn'
ORIGIN = HOST
LOGIN_URL = HOST + '/login'
LOGIN_AJAX = HOST + '/yiban_account/login_ajax'
USERNAME = 'username'
PASSWORD = 'password'


class IyibanCrawl(object):
    """
    Simple practice

    易班大学爬虫
    爬取课程信息（名称，机构，代码，报名人数及点赞人数）
    """
    def __init__(self, maxtasks=20):
        self.csvfile = 'c:\\iyiban\\iyiban.csv'
        self.path = 'c:\\iyiban'
        self.host = HOST
        self.urls = set()
        self.sem = asyncio.Semaphore(maxtasks)

    @asyncio.coroutine
    def get_login(self):
        """
        """
        session = yield from aiohttp.get(LOGIN_URL)
        self.csrf_token = session.cookies['csrftoken'].value
        self.cookies = session.cookies
        yield from session.release()

    @asyncio.coroutine
    def login(self, username, password):
        """
        """
        yield from self.get_login()
        s = yield from aiohttp.post(LOGIN_AJAX, data={
            'email': username,
            'password': password,
        }, headers={
            'X-CSRFToken': self.csrf_token,
            'User-Agent': USER_AGENT,
            'Referer': LOGIN_URL,
            'Origin': ORIGIN,
            'X-Requested-With': 'XMLHttpRequest',
        }, cookies=self.cookies)
        self.get = partial(aiohttp.get, headers={
            'X-CSRFToken': self.csrf_token
        }, cookies=s.cookies)
        a = yield from s.json()
        if a['success']:
            print('登录成功：', s.status)
        else:
            print('登录失败：', a['value'])
        yield from s.release()

    @asyncio.coroutine
    def run(self, page=1):
        if not hasattr(self, 'get'):
            yield from self.login(USERNAME, PASSWORD)

        r = yield from self.get(''.join([self.host, '/courses/page/', str(page)]))
        content = yield from r.text()
        yield from r.release()
        yield from self.sem.acquire()
        t1 = asyncio.Task(self.crawl(content))
        t1.add_done_callback(lambda x: self.sem.release())

        if re.compile(r'next-page').search(content):
            page += 1
            yield from self.sem.acquire()
            t = asyncio.Task(self.run(page))
            t.add_done_callback(lambda y: self.sem.release())

    @asyncio.coroutine
    def crawl(self, content):
        """
        """
        for j in HIT.findall(content):
            h, i, t = j
            yield from self.sem.acquire()
            task_1 = asyncio.Task(self.get_course_info(self.host+h))
            yield from self.sem.acquire()
            task_2 = asyncio.Task(self.download_image(self.host+i, t+'.jpg'))

            task_1.add_done_callback(lambda x: self.sem.release())
            task_2.add_done_callback(lambda y: self.sem.release())

    @asyncio.coroutine
    def get_course_info(self, u):
        """
        读取课程信息
        """
        r = yield from self.get(u)
        content = yield from r.text()
        yield from r.release()

        cont = JED.findall(content)
        if cont:
            j, e, d = JED.findall(content)[0]
            n, z, c = (
                N.findall(content)[0],
                Z.findall(content)[0][0],
                C.findall(content)[0][0],
            )

            print('Course name: %s' % n)
            yield from self.sem.acquire()
            print(self.sem)
            task = asyncio.Task(self.write_csv(n, j, d, e, z, c))
            task.add_done_callback(lambda x: self.sem.release())

    @asyncio.coroutine
    def write_csv(self, *args):
        """
        写入csv
        """
        with open(self.csvfile, 'a') as cf:
            writer = csv.writer(cf)
            writer.writerow([
                args[0],
                args[1],
                args[2],
                args[3],
                args[4],
                args[5]
            ])

    #@asyncio.coroutine
    async def download_image(self, u, n):
        f = os.path.join(self.path, n)
        r = await self.get(u)

        with open(f, 'wb') as fd:
            # fd.write(yield from r.read()) 会报语法错误，只能使用await。WTF
            fd.write(await r.read())
        self.sem.release()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    i = IyibanCrawl()
    asyncio.Task(i.run())

    loop.run_forever()
