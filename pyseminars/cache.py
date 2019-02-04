"""

Feed cache database.
There must be SEMINARINI environment variable with a path
to a INI file.

"""

import os
from configparser import ConfigParser
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Interval, Boolean
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import ArrowType

from ics import Calendar, Event

if 'SEMINARINI' not in os.environ:
    raise RuntimeError('SEMINARINI environment variable is not defined.')

config = ConfigParser()
with open(os.environ['SEMINARINI'], 'r') as f:
    config.read_file(f)


def now():
    """
    Returns TZ aware datetime
    """

    return datetime.utcnow().replace(tzinfo=timezone.utc)


Base = declarative_base()


class CachedFeed(Base):
    __tablename__ = 'feeds'

    feed_id = Column(Integer, primary_key=True)
    feed_last_download = Column(ArrowType)  # last time downloaded from website
    feed_name = Column(String(256))


class CachedEvent(Base):
    __tablename__ = 'events'

    # Fields
    event_id = Column(Integer, primary_key=True)
    event_last_download = Column(ArrowType)  # last time downloaded
    event_feed_id = Column(Integer)  # feed event belongs to
    event_ics_source = Column(String(256))  # URL

    # ICS fields
    name = Column(String(256))  # RFC5545 SUMMARY
    begin = Column(ArrowType)
    end = Column(ArrowType)
    duration = Column(Interval)
    uid = Column(String(256))
    description = Column(String(1024))
    created = Column(ArrowType)
    location = Column(String(256))
    url = Column(String(512))
    transparent = Column(Boolean)

    def to_ics_event(self):
        e = Event(name=self.name, begin=self.begin, end=self.end,
                  uid=self.uid,
                  description=self.description, created=self.created,
                  location=self.location, url=self.url,
                  transparent=self.transparent)
        return e

    def needs_updating(self):
        # Don't update events from the past
        # self.end is TZ aware, so we must compare with TZ aware datetime
        if self.end < now():
            return False

        # Needs update if refresh date is older than threshold
        interval_seconds = int(config['Database']['event_refresh_interval'])
        interval = timedelta(seconds=interval_seconds)
        threshold = now() - interval
        if self.event_last_download < threshold:
            return True

        return False

    @classmethod
    def from_ics_event(cls, download_date, feed_id, source_url, event):
        return CachedEvent(event_last_download=download_date,
                           event_feed_id=feed_id,
                           event_ics_source=source_url,
                           name=event.name,
                           begin=event.begin,
                           end=event.end,
                           duration=event.duration,
                           uid=event.uid,
                           description=event.description,
                           created=event.created,
                           location=event.location,
                           url=event.url,
                           transparent=event.transparent)


class Cache:

    def __init__(self):
        self.engine = create_engine(config['Database']['dburl'], echo=False)
        if not self.engine.dialect.has_table(self.engine, 'events'):
            CachedEvent.metadata.create_all(self.engine)
        if not self.engine.dialect.has_table(self.engine, 'feeds'):
            CachedFeed.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_events(self, download_date, feed_name, ics_url, events):
        session = self.Session()

        cached_feed = session.query(CachedFeed).filter_by(feed_name=feed_name)
        if cached_feed.count() == 0:
            cached_feed = CachedFeed(feed_last_download=download_date,
                                     feed_name=feed_name)
            session.add(cached_feed)
        elif cached_feed.count() > 1:
            raise RuntimeError('feed_name is not unique')
        else:
            cached_feed = cached_feed.first()
            cached_feed.feed_last_download = download_date

        for event in events:
            cached_event = session.query(CachedEvent).filter_by(uid=event.uid)
            if cached_event.count() == 0:
                cached_event = CachedEvent.from_ics_event(download_date,
                                                          cached_feed.feed_id,
                                                          ics_url,
                                                          event)
                session.add(cached_event)
            elif cached_event.count() > 1:
                raise RuntimeError('event uid is not unique')
            else:
                cached_event = cached_event.first()
                cached_event.event_last_download = download_date
                cached_event.event_feed_id = cached_feed['feed_id']
                cached_event.event_ics_source = ics_url
                cached_event.name = event.name
                cached_event.begin = event.begin
                cached_event.end = event.end
                cached_event.description = event.description
                cached_event.created = event.created
                cached_event.location = event.location
                cached_event.url = event.url
                cached_event.transparent = event.transparent
        session.commit()

    def get_events_from_source_url(self, ics_url):
        """
        Get events from cache.
        Returns None if the cache is out of date, or if specified event is not
        in cache
        """
        session = self.Session()
        q = session.query(CachedEvent).filter_by(event_ics_source=ics_url)
        if q.count() == 0:
            return None
        cached_events = q.all()
        for ce in cached_events:
            if ce.needs_updating():
                return None
        return {e.to_ics_event() for e in q.all()}

    def get_calendar(self, feed_name):
        """
        Returns Calendar object with all cached events
        """
        session = self.Session()
        feed = session.query(CachedFeed).filter_by(feed_name=feed_name)
        if feed.count() > 1:
            raise RuntimeError('feed_name is not unique')
        if feed.count() == 0:
            return Calendar()  # empty calendar
        feed = feed.first()
        c = Calendar()
        q = session.query(CachedEvent).filter_by(event_feed_id=feed.feed_id).order_by(CachedEvent.begin)
        c.events.update({e.to_ics_event() for e in q.all()})

        return c

    def feed_needs_updating(self, feed_name):
        session = self.Session()
        feed = session.query(CachedFeed).filter_by(feed_name=feed_name)
        if feed.count() > 1:
            raise RuntimeError('feed_name is not unique')
        if feed.count() == 0:
            return True
        feed = feed.first()
        interval_seconds = int(config['Database']['feed_refresh_interval'])
        interval = timedelta(seconds=interval_seconds)
        threshold = now() - interval
        if feed.feed_last_download < threshold:
            return True
        return False

    def print_content(self):
        session = self.Session()

        print('Cache content\n'
              '-------------')

        for feed_id, feed_name in session.query(CachedFeed.feed_id,
                                                CachedFeed.feed_name):
            print(feed_id, feed_name)
            q = session.query(CachedEvent.description,
                              CachedEvent.name,
                              CachedEvent.begin)
            for description, name, begin in q.filter_by(event_feed_id=feed_id):
                print(' '*4, description, '-', name, '-', begin)


if __name__ == '__main__':
    pass
