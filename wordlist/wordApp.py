import random
from itertools import groupby
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, redirect, render_template, send_from_directory, url_for

import dictionary

app = Flask(__name__)

WORDS_FILE = Path(__file__).parent / 'words.out'
WORDS = sorted({w.strip() for w in WORDS_FILE.read_text().splitlines() if w.strip()}, key=str.lower)


def display(word):
    return word.replace('_', ' ')


app.jinja_env.filters['display'] = display


@app.context_processor
def word_list():
    return {'all_words': WORDS}


@app.route('/')
def index():
    letters = [(k, list(g)) for k, g in groupby(WORDS, key=lambda w: w[0].upper())]
    return render_template('index.html', letters=letters)


@app.route('/random')
@app.route('/word')
def random_word():
    return redirect(url_for('word', myword=random.choice(WORDS)))


@app.route('/word/<path:myword>')
def word(myword):
    entry, error = None, None
    try:
        entry = dictionary.lookup(myword)
    except dictionary.WordNotFound:
        error = 'No dictionary entry found for “{}”.'.format(display(myword))
    except (dictionary.RateLimited, requests.RequestException) as e:
        error = 'Could not reach Wiktionary: {}'.format(e)

    neighbours = {'prev': None, 'next': None}
    if myword in WORDS:
        i = WORDS.index(myword)
        neighbours = {'prev': WORDS[i - 1], 'next': WORDS[(i + 1) % len(WORDS)]}

    return render_template('word.html', myword=myword, entry=entry, error=error,
                           **neighbours), (200 if entry else 404)


@app.route('/api/word/<path:myword>')
def api_word(myword):
    try:
        return jsonify(dictionary.lookup(myword))
    except dictionary.WordNotFound:
        abort(404)


@app.route('/api/words')
def api_words():
    return jsonify(WORDS)


@app.route('/offline')
def offline():
    return render_template('offline.html')


# The service worker must be served from the root so it can control every page.
@app.route('/sw.js')
def service_worker():
    response = send_from_directory(app.static_folder, 'sw.js', mimetype='text/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response


# Old URL scheme: /<myword>
@app.route('/<myword>')
def user_word(myword):
    return redirect(url_for('word', myword=myword))


if __name__ == '__main__':
    app.run(debug=True)
