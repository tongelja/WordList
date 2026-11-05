"""Render WordList as a static site (for Azure Static Web Apps) into ../dist.

Word data comes from data/words.json (see export_data.py). Words missing from
it are fetched from Wiktionary during the build, so adding a word to
words.out and pushing is enough.

    uv run python build_static.py [--out DIR]
"""
import argparse
import json
import os
import shutil
import time
from pathlib import Path

os.environ['WORDLIST_STATIC'] = '1'

import dictionary  # noqa: E402
import wordApp  # noqa: E402

HERE = Path(__file__).parent
DATA_FILE = HERE / 'data' / 'words.json'

AZURE_CONFIG = {
    'trailingSlash': 'auto',
    'responseOverrides': {'404': {'rewrite': '/404.html'}},
    'mimeTypes': {'.webmanifest': 'application/manifest+json', '.json': 'application/json'},
    'routes': [
        {'route': '/sw.js', 'headers': {'Cache-Control': 'no-cache'}},
        {'route': '/static/*', 'headers': {'Cache-Control': 'public, max-age=86400'}},
    ],
}


def load_data():
    data = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else {}
    real_lookup = dictionary.lookup
    fetched = []

    def lookup(word):
        if word not in data:
            if word not in wordApp.WORD_TO_SLUG:
                raise dictionary.WordNotFound(word)
            data[word] = real_lookup(word)
            fetched.append(word)
            time.sleep(1)
        entry = data[word]
        entry['quotations'].sort(key=lambda q: dictionary.literary_rank(q['author']))
        return entry

    dictionary.lookup = lookup
    return fetched


def write(out, url, body):
    path = out / url.lstrip('/')
    if url.endswith('/'):
        path = path / 'index.html'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(HERE.parent / 'dist'))
    args = parser.parse_args()
    out = Path(args.out)

    fetched = load_data()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(HERE / 'static', out / 'static')
    shutil.copy(HERE / 'static' / 'sw.js', out / 'sw.js')
    (out / 'staticwebapp.config.json').write_text(json.dumps(AZURE_CONFIG, indent=2))

    client = wordApp.app.test_client()
    pages = ['/', '/favorites/', '/offline/', '/404.html', '/api/words.json']
    skipped = []
    for word, slug in wordApp.WORD_TO_SLUG.items():
        try:
            dictionary.lookup(word)
        except dictionary.WordNotFound:
            skipped.append(word)
            continue
        except Exception as e:  # network trouble: leave the word out of this build
            print(f'  {word}: {e}')
            skipped.append(word)
            continue
        pages += ['/word/{}/'.format(slug), '/api/word/{}.json'.format(slug)]

    for url in pages:
        response = client.get(url)
        if response.status_code not in (200, 404) or (response.status_code == 404 and url != '/404.html'):
            raise SystemExit(f'{url} returned {response.status_code}')
        write(out, url, response.data)

    size = sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
    print(f'Built {len(pages)} files ({size / 1e6:.1f} MB) into {out}')
    if fetched:
        print(f'Fetched {len(fetched)} words not in {DATA_FILE.name}; run export_data.py to save them.')
    if skipped:
        print(f'No entry for {len(skipped)} words: ' + ', '.join(skipped))


if __name__ == '__main__':
    main()
