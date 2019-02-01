"""

Flask app serving the calendar

"""

from flask import Flask, Response, abort
from pyseminars.feeds import feeds

app = Flask(__name__)


@app.route("/<feed_name>.ics")
def main(feed_name):
    for f in feeds:
        if f.feed_name == feed_name:
            break
    else:
        return abort(404)
    c = f.generate_calendar()
    return Response(str(c), mimetype='text/calendar')


if __name__ == '__main__':
    app.run()
