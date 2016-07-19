#!/usr/bin/env python
#! encoding=utf-8

# Author        : gongzhengz@gmail.com
# Date          : 2016/07/13
# Description   : crawling the books from douban.com and export the data as Markdown format.
# Version       : 1.0.0.0
# Python Version: Python 2.7.3
# Python Queue  : https://docs.python.org/2/library/queue.html
# Beautiful Soup: http://beautifulsoup.readthedocs.io/zh_CN/v4.4.0/#

import os
import time
import timeit
import datetime
import re
import string
import urllib2
import math

from threading import Thread
from Queue import Queue
from bs4 import BeautifulSoup

gHeader = {"User-Agent": "Mozilla-Firefox5.0"}

# 书籍信息类
class BookInfo:
    name = ''
    url = ''
    icon = ''
    ratingNum = 0.0
    ratingPeople = 0
    comment = ''
    compositeRating = 0.0

    def __init__(self, name, url, icon, num, people, comment):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNum = num
        self.ratingPeople = people
        self.comment = comment
        self.compositeRating = num

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if self.url == other.url:
            return True
        return False

    def __sortByCompositeRating(self, other):
        val = self.compositeRating - other.compositeRating
        if val < 0:
            return 1
        elif val > 0:
            return -1
        else:
            val = self.ratingPeople - other.ratingPeople
            if val < 0:
                return 1
            elif val > 0:
                return -1
            else:
                return val

    def __cmp__(self, other):
        return self.__sortByCompositeRating(other)

# 获取 url 内容
def getHtml(url):
    try :
        request = urllib2.Request(url, None, gHeader)
        response = urllib2.urlopen(request)
        data = response.read().decode('utf-8')
        return data
    except urllib2.URLError, e :
        if hasattr(e, "code"):
            print "The server couldn't fulfill the request: " + url
            print "Error code: %s" % e.code
        elif hasattr(e, "reason"):
            print "We failed to reach a server. Please check your url: " + url + ", and read the Reason."
            print "Reason: %s" % e.reason
    return None

# 导出为 Markdown 格式文件
def exportToMarkdown(tag, books, total):
    path = "{0}.md".format(tag)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## 说明\n\n')
    file.write(' > 本页面是由 Python 爬虫根据图书推荐算法抓取豆瓣图书信息自动生成，列出特定主题排名靠前的一百本图书。  \n\n')
    file.write(' > 我使用的推荐算法似乎要比豆瓣默认的算法要可靠些，因为我喜欢书，尤其是对非虚构类图书有一定了解，'
        '所以我可以根据特定主题对推荐算法进行调整。大家可以访问 '
        '[豆瓣图书爬虫](https://github.com/luozhaohui/PythonSnippet/blob/master/exportTopBooksFromDouban.py) 查看推荐算法。'
        '希望能得到大家的反馈与建议，改善算法，提供更精准的图书排名。  \n\n')
    file.write(' > 联系方式：  \n')
    file.write('    + 邮箱：kesalin@gmail.com  \n')
    file.write('    + 微博：[飘飘白云](http://weibo.com/kesalin)  \n')

    file.write('\n## {0} Top {1} 图书\n\n'.format(tag, len(books)))
    file.write('### 总共分析了 {0} 本图书，更新时间：{1}\n'.format(total, todayStr))

    i = 0
    for book in books:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **图书名称**： [{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**： [{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **豆瓣评分**： {0}  \n'.format(book.ratingNum))
        file.write(' > **评分人数**： {0} 人  \n'.format(book.ratingPeople))
        file.write(' > **内容简介**： {0}  \n'.format(book.comment))
        i = i + 1
    file.close()

# 解析图书信息
def parseItemInfo(tag, minNum, maxNum, k, page, bookInfos):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("li", "subject-item")
    for item in items:
        #print item.prettify().encode('utf-8')

        # get book name
        bookName = ''
        content = item.find("h2")
        if content != None:
            href = content.find("a")
            if href != None:
                bookName = href['title'].strip().encode('utf-8')
                span = href.find("span")
                if span != None and span.string != None:
                    subTitle = span.string.strip().encode('utf-8')
                    bookName = '{0}{1}'.format(bookName, subTitle)
        #print " > name: {0}".format(bookName)

        # get description
        description = ''
        content = item.find("p")
        if content != None:
            description = content.string.strip().encode('utf-8')
        #print " > description: {0}".format(description)

        # get book url and image
        bookUrl = ''
        bookImage = ''
        content = item.find("div", "pic")
        if content != None:
            tag = content.find('a')
            if tag != None:
                bookUrl = tag['href'].encode('utf-8')
            tag = content.find('img')
            if tag != None:
                bookImage = tag['src'].encode('utf-8')
        #print " > url: {0}, image: {1}".format(bookUrl, bookImage)

        # get rating
        ratingNum = 0.0
        ratingPeople = 0
        content = item.find("span", "rating_nums")
        if content != None:
            ratingStr = content.string.strip().encode('utf-8')
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
        content = item.find("span", "pl")
        if content != None:
            ratingStr = content.string.strip().encode('utf-8')
            pattern = re.compile(r'(\()([0-9]*)(.*)(\))')
            match = pattern.search(ratingStr)
            if match:
                ratingStr = match.group(2).strip()
                if len(ratingStr) > 0:
                    ratingPeople = int(ratingStr)
        #print " > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople)

        # add book info to list
        bookInfo = BookInfo(bookName, bookUrl, bookImage, ratingNum, ratingPeople, description)
        bookInfo.compositeRating = computeCompositeRating(tag, minNum, maxNum, k, ratingNum, ratingPeople)
        bookInfos.append(bookInfo)

#=============================================================================
# 生产者-消费者模型
#=============================================================================
class Producer(Thread):
    url = ''

    def __init__(self, t_name, url, queue):
        Thread.__init__(self, name=t_name)
        self.url = url
        self.queue = queue

    def run(self):
        page = getHtml(self.url)
        if page != None:
            # block util a free slot available
            self.queue.put(page, True)

class Consumer(Thread):
    running = True
    tag = ''
    books = []
    queue = None
    minNum = 5
    maxNum = 5000
    k = 0.25

    def __init__(self, t_name, tag, minNum, maxNum, k, queue, books):
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.books = books
        self.tag = tag
        self.minNum = max(10, min(200, minNum))
        self.maxNum = max(1000, min(maxNum, 20000))
        self.k = max(0.01, min(1.0, k))

    def stop(self):
        self.running = False

    def run(self):
        while True:
            if self.running == False and self.queue.empty():
                break;

            page = self.queue.get()
            if page != None:
                parseItemInfo(self.tag, self.minNum, self.maxNum, self.k, page, self.books)
            self.queue.task_done()


def spider(tag, minNum, maxNum, k):
    print '   抓取 [{0}] 图书 ...'.format(tag)
    start = timeit.default_timer()

    # all producers
    queue = Queue(20)
    bookInfos = []
    producers = []

    # get first page of doulist
    url = "https://book.douban.com/tag/{0}".format(tag)
    page = getHtml(url)
    if page == None:
        print ' > invalid url {0}'.format(url)
    else:
        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        #print content.prettify().encode('utf-8')

        nextPageStart = 100000
        lastPageStart = 0
        for child in content.children:
            if child.name == 'a':
                pattern = re.compile(r'(start=)([0-9]*)(.*)(&type=)')
                match = pattern.search(child['href'].encode('utf-8'))
                if match:
                    index = int(match.group(2))
                    if nextPageStart > index:
                        nextPageStart = index
                    if lastPageStart < index:
                        lastPageStart = index

        # process current page
        #print " > process page : {0}".format(url)
        queue.put(page)

        # create consumer
        consumer = Consumer('Consumer', tag, minNum, maxNum, k, queue, bookInfos)
        consumer.start()

        # create producers
        producers = []
        for pageStart in range(nextPageStart, lastPageStart + nextPageStart, nextPageStart):
            pageUrl = "{0}?start={1:d}&type=T".format(url, pageStart)
            producer = Producer('Producer_{0:d}'.format(pageStart), pageUrl, queue)
            producer.start()
            producers.append(producer)
            #print " > process page : {0}".format(pageUrl)
            time.sleep(0.1)         # slow down a little

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        queue.put(None)
        consumer.join()

        # summrise
        total = len(bookInfos)
        elapsed = timeit.default_timer() - start
        print "   获取 %d 本 [%s] 图书信息，耗时 %.2f 秒"%(total, tag, elapsed)
        return bookInfos


def process(tags):
    tagList = tags[0].split(',')
    minNum = tags[1]
    maxNum = tags[2]
    k = tags[3]

    books = []
    # spider
    for tag in tagList:
        tagBooks = spider(tag.strip(), minNum, maxNum, k)
        books = list(set(books + tagBooks))

    total = len(books)
    print " > 共获取 {0} 本 [{1}] 不重复图书信息".format(total, tags[0])

    # sort
    books = sorted(books)
    # get top 100
    books = books[0:100]

    # export to markdown
    exportToMarkdown(tagList[0], books, total)

#=============================================================================
# 排序算法
#=============================================================================
def computeCompositeRating(tag, minNum, maxNum, k, num, people):
    people = max(1, min(maxNum, people))
    if people <= minNum:
        people = minNum / 3
    peopleWeight = math.pow(people, k)
    level4 = max(500, maxNum * 1 / 10)
    level5 = max(1000, maxNum * 3 / 10)
    if people < 50:
        return (num * 40 + peopleWeight * 60) / 100.0
    elif people < 100:
        return (num * 50 + peopleWeight * 50) / 100.0
    elif people < 200:
        return (num * 60 + peopleWeight * 40) / 100.0
    elif people < level4:
        return (num * 70 + peopleWeight * 30) / 100.0
    elif people < level5:
        return (num * 80 + peopleWeight * 20) / 100.0
    else:
        return (num * 90 + peopleWeight * 10) / 100.0

#=============================================================================
# 程序入口：抓取指定标签的书籍
#=============================================================================
if __name__ == '__main__':
    tags = [
        ["心理,心理学", 30, 3000, 0.25],
        ["社会,社会学", 30, 5000, 0.275],
        ["政治,政治学,自由主义", 30, 4000, 0.22],
        ["经济,经济学,金融", 30, 5000, 0.275],
        ["商业,投资,管理,创业", 30, 8000, 0.275],
        ["哲学,西方哲学,自由主义,思想", 30, 3000, 0.25],
        ["文化,人文,思想,国学", 30, 8000, 0.275],
        ["历史,中国历史,近代史", 30, 8000, 0.3],
        ["科技,科普,科学,神经网络", 30, 5000, 0.24],
        ["设计,用户体验,交互,交互设计,UCD,UE", 30, 3000, 0.25],
        ["编程,程序,算法,互联网", 30, 3000, 0.25],
        ["成长,教育", 50, 5000, 0.25],
        ["名著,外国名著,经典,古典文学", 50, 8000, 0.275],
        ["文学,经典,名著,外国名著,外国文学,中国文学,日本文学,当代文学", 50, 8000, 0.3],
        ["外国文学,外国名著,日本文学", 50, 8000, 0.3],
        ["中国文学", 50, 8000, 0.3],
        ["小说", 50, 8000, 0.3],
        ["杂文", 50, 5000, 0.25],
        ["散文", 50, 8000, 0.25],
        ["诗歌", 50, 4000, 0.25],
        ["科幻,科幻小说", 50, 8000, 0.275],
        ["推理,推理小说", 50, 8000, 0.275],
        ["武侠", 50, 8000, 0.3],
        ["悬疑", 50, 8000, 0.3],
        ["言情", 50, 8000, 0.3],
        ["青春,青春文学", 50, 8000, 0.3],
        ["童话", 20, 8000, 0.275],
        ["绘本", 20, 5000, 0.25],
        ["漫画,日本漫画", 50, 8000, 0.275],
    ]

    start = timeit.default_timer()

    for tag in tags:
        process(tag)

    elapsed = timeit.default_timer() - start
    print "== 总耗时 %.2f 秒 =="%(elapsed)
