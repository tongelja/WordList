"""Save every word in words.out to data/words.json for the static site build.

Reads the local cache (fetching from Wiktionary only for words not cached).
To start from the Pi's cache, run deploy/pull_data.sh instead.

    uv run python export_data.py
"""
import json
from pathlib import Path

import dictionary
from wordApp import WORDS

DATA_FILE = Path(__file__).parent / 'data' / 'words.json'


def main():
    data, missing = {}, []
    for word in WORDS:
        try:
            data[word] = dictionary.lookup(word)
        except dictionary.WordNotFound:
            missing.append(word)

    # One word per line keeps git diffs readable when words are added or change.
    DATA_FILE.parent.mkdir(exist_ok=True)
    lines = ['{}: {}'.format(json.dumps(w, ensure_ascii=False), json.dumps(e, ensure_ascii=False, sort_keys=True))
             for w, e in sorted(data.items())]
    DATA_FILE.write_text('{\n' + ',\n'.join(lines) + '\n}\n')
    print(f'Saved {len(data)} words to {DATA_FILE}; {len(missing)} have no entry: ' + ', '.join(missing))


if __name__ == '__main__':
    main()
