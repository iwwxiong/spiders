# coding: utf-8

import os
import requests
import uuid
import logging
import multiprocessing
from lxml.html import document_fromstring

"""
http://www.meizi.us爬虫
爬取所有页面并下载美女图片
"""
logger = logging.getLogger(__name__)
logging.basicConfig(filename='F:\\meizi.log', level=logging.DEBUG)

HOST = 'http://meizi.us/?page='
PATH = 'F:\\meizi'

def get_meinv_url(url_queue):
    for i in range(1, 120):
        try:
            url = HOST + str(i)
            res = requests.get(url, timeout=10)
            document = document_fromstring(res.content)
            src_list = document.xpath("//div[@class='row container-gallery']/div/div/div/a/img/@src")
            url_list = [i.replace('_small', '') for i in src_list]
            for url in url_list:
                url_queue.put(url)
        except:
            logger.debug('Meizi url is %s' % url)

def download_img(url_queue, lock):
    while True:
        lock.acquire()
        url = url_queue.get()
        lock.release()
        try:
            res = requests.get(url, timeout=10)
            img_name = str(uuid.uuid4()) + '.jpg'
            with open(os.path.join(PATH, img_name), 'wb') as img:
                img.write(res.content)
        except:
            logger.debug('Img url is %s' % url)


if __name__ == '__main__':
    url_queue = multiprocessing.Queue()
    lock  = multiprocessing.Lock()
    pw_meinv = multiprocessing.Process(target=get_meinv_url, args=(url_queue, ))
    pr = multiprocessing.Process(target=download_img, args=(url_queue, lock, ))
    pw_meinv.start()
    pr.start()
    pw_meinv.join()
    pr.terminate()
