"""Database creation
====================

"""

from pyseminars.cache import engine, CachedEvent, CachedFeed

CachedEvent.metadata.create_all(engine)
CachedFeed.metadata.create_all(engine)
