"""Print a word from the list (or one given with --word) to the terminal."""
import argparse
import json
import random
from pathlib import Path

import dictionary

WORDS_FILE = Path(__file__).parent / 'words.out'


class term_color:
    PURPLE = '\033[95m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'


def random_word():
    return random.choice([w for w in WORDS_FILE.read_text().splitlines() if w.strip()])


def label(name, text, color=term_color.YELLOW):
    print(color + name + ':' + term_color.END + ' ' + text)


def print_word(entry):
    print(term_color.BOLD + 'Word: ' + entry['word'] + term_color.END)
    for p in entry['pronunciations']:
        label('Pronunciation', p['ipa'] + (' (' + p['accent'] + ')' if p['accent'] else ''))
    for a in entry['audio']:
        label('Audio', a['url'])
    for e in entry['etymologies']:
        label('Etymology', e)
    for m in entry['meanings']:
        label('Category', m['pos'], term_color.GREEN)
        for d in m['definitions']:
            label('Definition', d['text'])
            for ex in d['examples'][:3]:
                label('Sentence', ex, term_color.PURPLE)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--word', help='Word to look up (default: random word from words.out)')
    parser.add_argument('--showRaw', action='store_true', help='Print the raw JSON')
    args = parser.parse_args()

    entry = dictionary.lookup(args.word or random_word())
    if args.showRaw:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
    else:
        print_word(entry)


if __name__ == '__main__':
    main()
