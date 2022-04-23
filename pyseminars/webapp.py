"""Flask app serving the calendar
=================================

"""

from importlib.resources import path
from flask import Flask, Response, abort, render_template, redirect, url_for
from flask_moment import Moment
from pyseminars.feeds import feeds
from pyseminars.cache import Cache, now
import pyseminars

with path(pyseminars, "templates") as template_folder, path(
    pyseminars, "static"
) as static_folder:
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
moment = Moment(app)


@app.route("/<feed_name>.ics")
def calendar(feed_name):
    for f in feeds:
        if f.feed_name == feed_name:
            break
    else:
        return abort(404)
    with Cache() as cache:
        c = f.generate_calendar(cache)
    return Response(str(c), mimetype="text/calendar")


@app.route("/<feed_name>")
def feed(feed_name):
    for f in feeds:
        if f.feed_name == feed_name:
            break
    else:
        return abort(404)
    with Cache() as cache:
        c = f.generate_calendar(cache)
        download_date = cache.feed_download_date(feed_name)
    th = now()
    past_events = {e for e in c.events if e.end < th and (e.description or e.name)}
    upcoming_events = {e for e in c.events if e.end >= th and (e.description or e.name)}
    return render_template(
        "main.html",
        feeds=feeds,
        feed_name=feed_name,
        feed_info=f,
        feed_download_date=download_date,
        past_events=sorted(past_events, key=lambda e: e.begin),
        upcoming_events=sorted(upcoming_events, key=lambda e: e.begin),
    )


@app.route("/")
def main():
    return redirect(url_for("feed", feed_name=feeds[0]))


if __name__ == "__main__":
    app.run()
