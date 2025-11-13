#!/usr/bin/env python
# coding: utf-8

# NHK Featured Article Scraper

# In[1]:


import scrapy
import sqlite3
from itemloaders.processors import TakeFirst
from scrapy.loader import ItemLoader
import re
from datetime import datetime
import json
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


# In[2]:


#scrapes NHK news featured articles

def text_cleaner(text_raw):
    clean_text = []
    for t in text_raw:
        t = t.strip()
        if t:
            clean_text.append(t)
    return clean_text
        
class ArticleItem(scrapy.Item):
    url = scrapy.Field(output_processor = TakeFirst())
    title = scrapy.Field(output_processor = TakeFirst())
    date = scrapy.Field(output_processor = TakeFirst())
    topic = scrapy.Field(output_processor = TakeFirst())
    body = scrapy.Field(output_processor = TakeFirst())

class ArticleSpider(scrapy.Spider):

    start_urls = ['https://www3.nhk.or.jp/news/json16/feature/0002509_all.json',
                 'https://www3.nhk.or.jp/news/json16/feature/0002505_all.json',
                 'https://www3.nhk.or.jp/news/json16/feature/0002508_all.json',
                 'https://www3.nhk.or.jp/news/json16/feature/0002506_all.json',
                 'https://www3.nhk.or.jp/news/json16/feature/0002510_all.json',
                 'https://www3.nhk.or.jp/news/json16/feature/0002511_all.json']
    
    topic_list = ['business','society','politics','weather','international','sports']
    topic_mapped = dict(zip(start_urls,topic_list))
    
    name = 'nhk'
    custom_settings = {
    'ITEM_PIPELINES': {
        '__main__.SQLitePipeline': 300},
    'ROBOTSTXT_OBEY': True,
    'DOWNLOAD_DELAY': 3,
    'AUTOTHROTTLE_ENABLED' : True
    }
    
    def parse(self, response):
        
        df = json.loads(response.body)
        feed_topic = self.topic_mapped[response.url]

        channel = df['channel']
        layout = channel["layout"]
        article_dict_list = layout[0]["link_group"]
        
        
        for article in article_dict_list:
            raw_article_url = article["url"]
            cleaned_url = raw_article_url.replace("\\/", "/")
            full_article_url = urljoin('https://www3.nhk.or.jp', cleaned_url)
            
            title = article['link_name']
            date = article["date"]
            #if full_article_url.startswith("https://www3.nhk.or.jp/news/html/"):
            yield scrapy.Request(
                url=full_article_url,
                callback=self.parse_single,
                meta={'topic': feed_topic, 'title':title, 'date': date})
            #else:
                #pass

            
    def parse_single(self, response):
        loader = ItemLoader(item = ArticleItem(), selector=response)
        try:
            loader.add_value('url',response.url)
        except:
            print("Unable to add url item")

        try:
            loader.add_value("title", response.meta['title'])
        except:
            print("Unable to add title item")

        
        try:
            date = datetime.strptime(response.meta['date'], "%a, %d %b %Y %H:%M:%S %z")
            new_date = date.strftime("%Y-%m-%d %H:%M:%S %z")
            loader.add_value('date', new_date)
        except:
            print("Unable to add date item")
            
        try:
            loader.add_value('topic', response.meta['topic'])
        except:
            print("Unable to add topic item")

        #Checks various source paths to article text. Due to NHK's consistent changes in source paths, some sources may be skipped
        try:
            body_sources = [
                        'section.content--body',
                        'div.entry-content',
                        'div.article__content',
                        'section.module--detail-content',
                        'div.content--detail-body',
                        'section.detailBlock',
                        'div.content--detail-main',
                        'article.module module--detail detail-tokushu']
            for x in body_sources:
                raw_text = response.css(f'{x} *::text').getall()
                if raw_text:
                    print(x,' was successful')
                    clean_text = text_cleaner(raw_text)
                    loader.add_value('body', ' '.join(clean_text))
                    break
        except:
            print("Unable to add body item")
        
        yield loader.load_item()

#creates and populates SQLite database        
class SQLitePipeline:
    def open_spider(self,spider):
        self.db = sqlite3.connect('nhk_featured_articles.db')
        self.cur = self.db.cursor()
        drop_table = "DROP TABLE IF EXISTS NHK_Articles"
        articles_table = """
            CREATE TABLE if not exists NHK_Articles(
              URL Text Not Null,
              Title Text Not Null,
              Topic Text Not Null,
              Date Text,
              Body Text Not Null,
             

              CONSTRAINT article_URL_PK
                Primary KEY(URL)
            )
            """
        self.cur.execute(drop_table)
        self.cur.execute(articles_table)
        self.cur.connection.commit()
        
    def close_spider(self, spider):
        self.db.close()
        
    def process_item(self,item,spider):
        self.cur.execute("Insert into NHK_Articles Values(?,?,?,?,?)",
            (item.get('url'),
            item.get('title'),
            item.get('topic'),
            item.get('date'),
            item.get('body')))
        self.cur.connection.commit()
        return item
    
process = CrawlerProcess()
process.crawl(ArticleSpider)
process.start()


# In[3]:


import pandas as pd 
db = sqlite3.connect('nhk_featured_articles.db')
cursor = db.cursor()

raw_article_data = cursor.execute('SELECT * from NHK_Articles').fetchall()
df = pd.DataFrame(raw_article_data)
csv_data = df.to_csv()
csvfile = open('nhk_articles.csv', 'w',encoding='utf-8-sig')
csvfile.write(csv_data)
csvfile.close()






