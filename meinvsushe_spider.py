# coding: utf-8

import os
import uuid
import logging
import requests
import functools
import multiprocessing
from lxml import etree
from Queue import Queue
from lxml.html import HtmlMixin
from lxml.html import document_fromstring


class WHtmlElement(etree.ElementBase, HtmlMixin):
    def xpath(self, query):
        print query


class WHtmlElementClassLookup(etree.CustomElementClassLookup):
    """A lookup scheme for HTML Element classes.

    To create a lookup instance with different Element classes, pass a tag
    name mapping of Element classes in the ``classes`` keyword argument and/or
    a tag name mapping of Mixin classes in the ``mixins`` keyword argument.
    The special key '*' denotes a Mixin class that should be mixed into all
    Element classes.
    """
    _default_element_classes = {}

    def __init__(self, classes=None, mixins=None):
        etree.CustomElementClassLookup.__init__(self)
        if classes is None:
            classes = self._default_element_classes.copy()
        if mixins:
            mixers = {}
            for name, value in mixins:
                if name == '*':
                    for n in classes.keys():
                        mixers.setdefault(n, []).append(value)
                else:
                    mixers.setdefault(name, []).append(value)
            for name, mix_bases in mixers.items():
                cur = classes.get(name, WHtmlElement)
                bases = tuple(mix_bases + [cur])
                classes[name] = type(cur.__name__, bases, {})
        self._element_classes = classes

    def lookup(self, node_type, document, namespace, name):
        if node_type == 'element':
            return self._element_classes.get(name.lower(), WHtmlElement)
        # Otherwise normal lookup
        return None


class WHTMLParser(etree.HTMLParser):
    def __init__(self, **kwargs):
        super(WHTMLParser, self).__init__(**kwargs)
        self.set_element_class_lookup(WHtmlElementClassLookup())


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

HOST = 'http://www.meinvsushe.com/'
# 存储路径
PATH = 'F:\\meinvsushe'
headers = {
    'Referer': 'http://www.meinvsushe.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36',
}

# 美女宿舍名站url
mingzhan_url = [
    'http://www.meinvsushe.com/forum-42-1.html',
    'http://www.meinvsushe.com/forum-39-1.html',
    'http://www.meinvsushe.com/forum-40-1.html',
    'http://www.meinvsushe.com/forum-41-1.html',
]

# 美女宿舍本站url
meinv_url = [
    'http://www.meinvsushe.com/forum-36-1.html',
    'http://www.meinvsushe.com/forum-37-1.html',
    'http://www.meinvsushe.com/forum-45-1.html',
]

def get_content(url_queue, xpath, title, url):
    url = HOST + url
    res = requests.get(url)
    document = document_fromstring(res.content)
    target = {}
    target[title] = document.xpath(xpath)
    url_queue.put(target)

def get_mingzhan_initial(url_queue, url):
    res = requests.get(url)
    document = document_fromstring(res.content)
    has_next = document.xpath('//a[@class="nxt"]/@href')
    url_list = document.xpath('//div[@class="c cl"]/a/@href')
    title_list = document.xpath('//div[@class="c cl"]/a/@title')
    func = functools.partial(get_content, url_queue, "//td[@class='t_f']/img/@file")
    for i in range(len(title_list)):
        func(title_list[i], url_list[i])

    if has_next:
        next_url = HOST + has_next[0]
        return get_initial(url_queue, next_url)

def get_meinv_initial(url_queue, url):
    res = requests.get(url)
    document = document_fromstring(res.content)
    url_list = document.xpath('//div[@class="c cl"]/a/@href')
    title_list = document.xpath('//div[@class="c cl"]/a/@title')
    func = functools.partial(get_content, url_queue, '//td[@class="t_f"]/ignore_js_op/img/@file')
    for i in range(len(title_list)):
        func(title_list[i], url_list[i])

def save_meinv_img(path, url):
    if not os.path.exists(path):
        os.mkdir(path)

    # 默认保存所有图片为jpg格式
    try:
        img_name = str(uuid.uuid4()) + '.jpg'
        res = requests.get(url, headers=headers)
        with open(os.path.join(path, img_name), 'wb') as img:
            img.write(res.content)
    except:
        logger.debug('This %s is failed.' % url)

def download_img(url_queue, lock):
    while True:
        lock.acquire()
        img = url_queue.get(True)
        lock.release()
        path = os.path.join(PATH, img.keys()[0])
        func = functools.partial(save_meinv_img, path)

        for url in img.values()[0]:
            if 'http' not in url:
                url = HOST + url
            func(url)

def meinv_initial(url_queue, target_url):
    func = functools.partial(get_meinv_initial, url_queue)
    for url in target_url:
        func(url)
    #map(func, target_url)

def mingzhan_initial(url_queue, target_url):
    func = functools.partial(get_mingzhan_initial, url_queue)
    for url in target_url:
        func(url)
    #map(func, target_url)

if __name__ == '__main__':
    """
    美女宿舍图片爬虫
    本站和名站图片路径不一样，名站图片是外站链接。古分开爬取
    """
    url_queue = multiprocessing.Queue()
    lock  = multiprocessing.Lock()
    pw_mingzhan = multiprocessing.Process(target=mingzhan_initial, args=(url_queue, mingzhan_url,))
    pw_meinv = multiprocessing.Process(target=meinv_initial, args=(url_queue, meinv_url,))
    pw_mingzhan.start()
    pw_meinv.start()
    # pool = multiprocessing.Pool(4)
    # for i in range(4):
    #     pool.apply_async(download_img, (url_queue,lock, ))
    for i in range(5):
        pr = multiprocessing.Process(target=download_img, args=(url_queue,lock, ))
        pr.start()
    # pool.close()
    # pool.join()
    pw_mingzhan.join()
    pw_meinv.join()
    pr.terminate()

