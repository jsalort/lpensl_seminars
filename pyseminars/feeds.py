"""

This submodule parse the RSS feeds

"""

from datetime import datetime
from configparser import ConfigParser
from importlib_resources import open_text
from pprint import pprint

import feedparser
from ics import Calendar, Event
import requests

import pyseminars

config = ConfigParser()
with open_text(pyseminars, 'feeds_lpensl.ini') as f:
    config.read_file(f)


class SeminarFeed:
    """

    This class represents one RSS feed

    """

    def __init__(self, feed_name):
        self.feed_name = feed_name
        self.feed_url = config[feed_name]['feed']
        self.feed_title = config[feed_name]['title']
        self.feed_webpage = config[feed_name]['webpage']
        self.begin_hour = int(config[feed_name]['begin_hour'])
        self.begin_min = int(config[feed_name]['begin_min'])
        self.end_hour = int(config[feed_name]['end_hour'])
        self.end_min = int(config[feed_name]['end_min'])

    def __str__(self):
        return self.feed_name

    def generate_calendar(self):
        feed_data = feedparser.parse(self.feed_url)
        c = Calendar()
        for item in feed_data["items"]:
            ics_url = item['link'] + '/ics_view'
            r = requests.get(ics_url)
            item_cal = Calendar(r.text)
            c.events.update(item_cal.events)
        return c


feeds = [SeminarFeed(name) for name in config.sections()]

if __name__ == '__main__':
    for feed in feeds:
        print(feed.feed_title)
        print(feed.feed_url)
        print(feed.feed_data["version"])
        print('---')

    items = feed.feed_data["items"]
    pprint(items[0])

    print(feed.generate_calendar())
