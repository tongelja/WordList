"""Download every word in words.out into the cache, slowly enough to stay
within Wiktionary's rate limits. Safe to stop and re-run: cached words are skipped.

    uv run python prefetch.py [--delay SECONDS]
"""
import argparse
import time
from pathlib import Path

import requests

import dictionary

WORDS_FILE = Path(__file__).parent / 'words.out'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delay', type=float, default=1.0, help='Seconds to wait between words')
    args = parser.parse_args()

    words = [w.strip() for w in WORDS_FILE.read_text().splitlines() if w.strip()]
    todo = [w for w in words if not dictionary.cache_path(w).exists()]
    print(f'{len(words)} words, {len(words) - len(todo)} already cached, {len(todo)} to fetch', flush=True)

    missing = []
    for i, word in enumerate(todo, 1):
        for attempt in range(3):
            try:
                dictionary.lookup(word)
                break
            except dictionary.WordNotFound:
                missing.append(word)
                break
            except (dictionary.RateLimited, requests.RequestException) as e:
                print(f'  {word}: {e}; waiting a minute', flush=True)
                time.sleep(60)
        if i % 50 == 0:
            print(f'{i}/{len(todo)} fetched', flush=True)
        time.sleep(args.delay)

    print(f'Done. {len(missing)} words have no Wiktionary entry:', flush=True)
    for word in missing:
        print('  ' + word, flush=True)


if __name__ == '__main__':
    main()
