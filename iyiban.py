#!/usr/bin/env python3
# coding: utf-8

import os
import re
import csv
import asyncio
import aiohttp
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

HIT = re.compile(r'<div\sclass="yb-for-img">.+?<a\shref="(.*?)">.+?<img\ssrc="(.*?)"\swidth.*?>.*?title="(.*?)"\>', re.DOTALL)
JED = re.compile(r'<ul\sclass="fcw\sclearfix">.+?<li>提供学校：(.*?)<\/li>.+?<span>(\d+?)<\/span>.+?<li\s.+?>课程代码：(.*?)<\/li>', re.DOTALL)
Z = re.compile(r'<em\sid="favorites">(\d+?)<\/em>', re.DOTALL)
C = re.compile(r'<em\sid="unfavorites">(\d+?)<\/em>', re.DOTALL)
N = re.compile(r'<h1\sclass="fcw".*?">(.*?)<\/h1>', re.DOTALL)


class IyibanCrawl(object):
    """
    Simple practice

    易班大学爬虫
    爬取课程信息（名称，机构，代码，报名人数及点赞人数）
    """
    def __init__(self, maxtasks=20):
        self.csvfile = 'c:\\iyiban\\iyiban.csv'
        self.path = 'c:\\iyiban'
        self.host = 'http://www.iyiban.cn'
        self.urls = set()
        self.sem = asyncio.Semaphore(maxtasks)

    @asyncio.coroutine
    def run(self, page=1):
        r = yield from aiohttp.get(''.join([self.host, '/courses/page/', str(page)]))
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
        r = yield from aiohttp.get(u)
        content = yield from r.text()
        yield from r.release()

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
        r = await aiohttp.get(u)

        with open(f, 'wb') as fd:
            # fd.write(yield from r.read()) 会报语法错误，只能使用await。WTF
            fd.write(await r.read())
        self.sem.release()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    i = IyibanCrawl()
    asyncio.Task(i.run())
    loop.run_forever()
