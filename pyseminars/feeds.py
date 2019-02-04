"""

This submodule parse the RSS feeds

"""

from configparser import ConfigParser
from pprint import pprint
from importlib_resources import open_text

import feedparser
from ics import Calendar
import requests

import pyseminars
from pyseminars.cache import Cache, now

config = ConfigParser()
with open_text(pyseminars, 'feeds_lpensl.ini') as f:
    config.read_file(f)
cache = Cache()


class SeminarFeed:
    """

    This class represents one RSS feed

    """

    def __init__(self, feed_name):
        self.feed_name = feed_name
        self.feed_url = config[feed_name]['feed']
        self.feed_title = config[feed_name]['title']
        self.feed_webpage = config[feed_name]['webpage']

    def __str__(self):
        return self.feed_name

    def generate_calendar(self):
        c = cache.get_calendar(self.feed_name)
        if cache.feed_needs_updating(self.feed_name):
            print('Downloading RSS feed')
            feed_data = feedparser.parse(self.feed_url)
            for item in feed_data["items"]:
                ics_url = item['link'] + '/ics_view'
                events = cache.get_events_from_source_url(ics_url)
                if not events:
                    print('Downloading ics')
                    r = requests.get(ics_url)
                    item_cal = Calendar(r.text)
                    cache.save_events(now(), self.feed_name,
                                      ics_url, item_cal.events)
                    events = item_cal.events
                else:
                    print('Using cached ics')
                c.events.update(events)
        else:
            print('Using cached calendar')
        return c


feeds = [SeminarFeed(name) for name in config.sections()]

if __name__ == '__main__':
    cal = feeds[0].generate_calendar()
    cal2 = feeds[1].generate_calendar()
    print('Cal\n' + '-'*3)
    pprint(cal.events)
    #cache.print_content()
