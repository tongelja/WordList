import hashlib
import os
import random
import re
import unicodedata
from itertools import groupby
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, redirect, render_template, send_from_directory, url_for

import dictionary

app = Flask(__name__)
# Set when build_static.py renders the site to plain files (no live lookups).
app.config['STATIC_SITE'] = bool(os.environ.get('WORDLIST_STATIC'))

WORDS_FILE = Path(__file__).parent / 'words.out'
WORDS = sorted({w.strip() for w in WORDS_FILE.read_text().splitlines() if w.strip()}, key=str.lower)


def display(word):
    return word.replace('_', ' ')


def slugify(word):
    """'Hobson’s_choice' -> 'hobsons-choice', 'déclassé' -> 'declasse'."""
    ascii_word = unicodedata.normalize('NFKD', word).encode('ascii', 'ignore').decode()
    ascii_word = re.sub(r"['’]", '', ascii_word.lower())
    return re.sub(r'[^a-z0-9]+', '-', ascii_word).strip('-') or 'word'


SLUG_TO_WORD, WORD_TO_SLUG = {}, {}
for w in WORDS:
    slug, n = slugify(w), 2
    while slug in SLUG_TO_WORD:
        slug, n = '{}-{}'.format(slugify(w), n), n + 1
    SLUG_TO_WORD[slug] = w
    WORD_TO_SLUG[w] = slug


def word_url(word):
    if word in WORD_TO_SLUG:
        return url_for('word', myword=WORD_TO_SLUG[word]) + '/'
    return url_for('word', myword=word)


def resolve(myword):
    """A URL segment is either a slug from the list or a free-typed word."""
    myword = myword.strip('/')
    return SLUG_TO_WORD.get(myword, myword)


LOWER_TO_WORD = {display(w).lower(): w for w in WORDS}


def listed_word(text):
    """The list's spelling of a synonym or antonym, if that word is in the list."""
    return LOWER_TO_WORD.get(text.replace('’', "'").lower()) or LOWER_TO_WORD.get(text.lower())


app.jinja_env.filters['display'] = display
app.jinja_env.globals['word_url'] = word_url
app.jinja_env.globals['listed_word'] = listed_word


def asset(filename):
    """/static/<file>?v=<hash>, so a changed file is never served from an old cache."""
    digest = hashlib.sha1((Path(app.static_folder) / filename).read_bytes()).hexdigest()[:8]
    return url_for('static', filename=filename, v=digest)


app.jinja_env.globals['asset'] = asset


@app.context_processor
def site_info():
    return {'all_words': WORDS, 'static_site': app.config['STATIC_SITE']}


@app.route('/')
def index():
    letters = [(k, list(g)) for k, g in groupby(WORDS, key=lambda w: w[0].upper())]
    return render_template('index.html', letters=letters)


@app.route('/random')
@app.route('/word')
def random_word():
    return redirect(word_url(random.choice(WORDS)))


@app.route('/word/<path:myword>')
def word(myword):
    myword = resolve(myword)
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
        return jsonify(dictionary.lookup(resolve(myword.removesuffix('.json'))))
    except dictionary.WordNotFound:
        abort(404)


# The search box, random button and offline page all read this one file,
# so the full list isn't repeated in every page.
@app.route('/api/words.json')
def api_words():
    return jsonify([{'word': display(w), 'url': word_url(w)} for w in WORDS])


@app.route('/favorites/')
def favorites():
    return render_template('favorites.html')


@app.route('/offline/')
def offline():
    return render_template('offline.html')


@app.route('/404.html')
def not_found():
    return render_template('notfound.html'), 404


# The service worker must be served from the root so it can control every page.
@app.route('/sw.js')
def service_worker():
    response = send_from_directory(app.static_folder, 'sw.js', mimetype='text/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response


# Old URL scheme: /<myword>
@app.route('/<myword>')
def user_word(myword):
    return redirect(word_url(myword))


if __name__ == '__main__':
    app.run(debug=True)
