"""Word lookups against Wiktionary (free, no API key).

Replaces the old Oxford Dictionaries API, which has been shut down.
"""
import functools
import hashlib
import html
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

# Wikimedia asks API clients to identify themselves with a contact address;
# set WORDLIST_CONTACT (an email or URL) to get friendlier rate limits.
USER_AGENT = 'WordList/1.0 (personal vocabulary app; {})'.format(
    os.environ.get('WORDLIST_CONTACT', 'no contact set'))
REST_URL = 'https://en.wiktionary.org/api/rest_v1/page/definition/'
PARSE_URL = 'https://en.wiktionary.org/w/api.php'
PAGE_URL = 'https://en.wiktionary.org/wiki/'
CACHE_VERSION = 'v3'
CACHE_DIR = Path(os.environ.get('WORDLIST_CACHE', Path(__file__).parent / '.cache'))

session = requests.Session()
session.headers['User-Agent'] = USER_AGENT


class WordNotFound(Exception):
    pass


class RateLimited(Exception):
    pass


def fetch(url, **kwargs):
    for attempt in range(4):
        r = session.get(url, timeout=15, **kwargs)
        if r.status_code != 429:
            return r
        wait = r.headers.get('Retry-After', '')
        time.sleep(min(int(wait), 30) if wait.isdigit() else 2 ** attempt)
    raise RateLimited('Wiktionary is rate-limiting requests; try again shortly.')


def candidate_titles(word):
    """Wiktionary titles to try for a word from the list (e.g. 'Hobson’s_choice')."""
    base = word.strip().replace('_', ' ').replace('’', "'")
    seen = []
    for title in (base, base.lower(), base[:1].upper() + base[1:]):
        if title and title not in seen:
            seen.append(title)
    return seen


def html_to_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.select('style, sup.reference, .mw-editsection'):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text()).strip()


def get_definitions(title):
    r = fetch(REST_URL + quote(title, safe=''))
    if r.status_code == 404:
        return None
    r.raise_for_status()

    meanings = []
    for entry in r.json().get('en', []):
        definitions = []
        for d in entry.get('definitions', []):
            # A definition containing its own <ol> is a group heading that repeats
            # its sub-definitions (and their examples), which are listed next anyway.
            if '<ol' in d.get('definition', ''):
                continue
            text = html_to_text(d.get('definition', ''))
            if not text:
                continue
            examples = [html_to_text(e) for e in d.get('examples', [])]
            definitions.append({'text': text, 'examples': [e for e in examples if e]})
        if definitions:
            meanings.append({'pos': entry.get('partOfSpeech', ''), 'definitions': definitions})
    return meanings


def english_section(html):
    """Return the top-level nodes belonging to the ==English== section."""
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h2', id='English')
    if heading is None:
        return []
    start = heading.parent if 'mw-heading' in heading.parent.get('class', []) else heading
    nodes = []
    for node in start.find_next_siblings():
        if 'mw-heading2' in node.get('class', []) or node.name == 'h2':
            break
        nodes.append(node)
    return nodes


def heading_text(node):
    h = node.find(re.compile('^h[2-6]$')) if 'mw-heading' in node.get('class', []) else None
    if h is None and re.fullmatch('h[2-6]', node.name or ''):
        h = node
    return h.get_text().strip() if h else None


# Authors whose quotations are shown first, in this order:
# classic literature, then philosophy, then everyone else (in Wiktionary's order).
LITERARY_AUTHORS = [
    # Classic literature
    'Shakespeare', 'King James', 'Milton', 'Chaucer', 'Spenser', 'Marlowe', 'Donne', 'Ben Jonson',
    'Dryden', 'Alexander Pope', 'Jonathan Swift', 'Defoe',
    'Samuel Johnson', 'Fielding', 'Jane Austen', 'Wordsworth', 'Coleridge', 'Byron',
    'Shelley', 'Keats', 'Walter Scott', 'Dickens', 'Brontë', 'Thackeray', 'George Eliot',
    'Tennyson', 'Browning', 'Hawthorne', 'Melville', 'Edgar Allan Poe', 'Whitman', 'Emily Dickinson',
    'Mark Twain', 'Thomas Hardy', 'Henry James',
    'Oscar Wilde', 'Robert Louis Stevenson', 'Arthur Conan Doyle', 'Joseph Conrad',
    'Kipling', 'Edith Wharton', 'James Joyce', 'Virginia Woolf', 'Fitzgerald',
    'Hemingway', 'Orwell', 'T. S. Eliot', 'Steinbeck', 'Faulkner', 'Nabokov',
    # Philosophers and essayists (Jowett and Florio translated Plato and Montaigne)
    'Francis Bacon', 'Plato', 'Jowett', 'Aristotle', 'Marcus Aurelius', 'Seneca', 'Cicero', 'Montaigne', 'Florio',
    'Thomas More', 'Thomas Hobbes', 'John Locke', 'David Hume', 'George Berkeley', 'Edmund Burke',
    'Adam Smith', 'Rousseau', 'Voltaire', 'Immanuel Kant', 'Mary Wollstonecraft', 'Thomas Paine',
    'Jeremy Bentham', 'John Stuart Mill', 'Ralph Waldo Emerson', 'Henry David Thoreau',
    'Thomas Carlyle', 'Schopenhauer', 'Kierkegaard', 'Nietzsche', 'William James',
    'Bertrand Russell', 'Robert Burton', 'Thomas Browne', 'Pascal',
]


def literary_rank(author):
    for i, name in enumerate(LITERARY_AUTHORS):
        if name.lower() in author.lower():
            return i
    return len(LITERARY_AUTHORS)


def passage_html(span):
    """Plain text of a quoted passage, keeping only <b> around the headword."""
    parts = []
    for child in span.descendants:
        if isinstance(child, str) and not child.find_parent('b'):
            parts.append(html.escape(child))
        elif getattr(child, 'name', None) == 'b':
            parts.append('<b>' + html.escape(child.get_text()) + '</b>')
        elif getattr(child, 'name', None) == 'br':
            parts.append(' / ')
    return re.sub(r'\s+', ' ', ''.join(parts)).replace('ſ', 's').strip()


def parse_quotation(citation):
    source = citation.select_one('.cited-source')
    passage = citation.select_one('.cited-passage')
    if source is None or passage is None:
        return None

    year = source.find('b')
    year = year.get_text(strip=True) if year else ''
    cite = source.find('cite')
    work = cite.get_text(' ', strip=True) if cite else ''
    work = re.sub(r'\s*\[\s*…\s*\]', '', work).replace(' ,', ',').strip(' ,:')

    # The text before <cite> reads like "c. 1599 (date written), [William Shakespeare], in".
    # Authors are usually linked to Wikipedia; otherwise take the first plain chunk.
    before = []
    for node in source.children:
        if node is cite:
            break
        before.append(node)
    links = [a.get_text(strip=True) for n in before if hasattr(n, 'find_all')
             for a in ([n] if n.name == 'a' else n.find_all('a')) if 'extiw' in a.get('class', [])]
    if links:
        author = links[0]
    else:
        text = ''.join(n.get_text() if hasattr(n, 'get_text') else str(n) for n in before)
        text = re.sub(r'\([^)]*\)|\[pseudonym[^\]]*\]?', '', text).replace(year, '', 1)
        chunks = [c.replace('[', '').replace(']', '').strip(' “”" ') for c in text.split(',')]
        author = next((c for c in chunks if c and not re.match(
            r'^(in|chapter|act|book|canto|part|c\.|a\.|p\.)$|^(in|chapter|act|book|canto|part)\b'
            r'|^(January|February|March|April|May|June|July|August|September|October|November|December) \d',
            c, re.I)), '')
    author = author.replace('[', '').replace(']', '')

    text = passage_html(passage)
    if not text:
        return None
    return {'year': year, 'author': author, 'work': work, 'passage': text}


def nym_words(node):
    """English words linked in a "Synonyms: …" line or a Synonyms/Antonyms list,
    leaving out "see also Thesaurus:…" links."""
    words = []
    for span in node.select('span[lang="en"]'):
        link = span.find_parent('a')
        if link is not None and link.get('title', '').startswith('Thesaurus:'):
            continue
        text = span.get_text(' ', strip=True)
        if text:
            words.append(text)
    return words


def get_page_details(title):
    r = fetch(PARSE_URL, params={
        'action': 'parse', 'page': title, 'prop': 'text',
        'format': 'json', 'formatversion': 2, 'redirects': 1,
    })
    r.raise_for_status()
    html = r.json().get('parse', {}).get('text', '')

    ipa, audio, etymologies, quotations = [], [], [], []
    nyms = {'synonym': [], 'antonym': []}
    section = None
    for node in english_section(html):
        # Per-sense lines under a definition: "Synonyms: glad, joyful; see also Thesaurus:happy".
        for kind in nyms:
            for span in node.select('span.nyms.' + kind):
                nyms[kind] += nym_words(span)

        for citation in node.select('div.citation-whole'):
            if (q := parse_quotation(citation)):
                quotations.append(q)

        heading = heading_text(node)
        if heading is not None:
            section = heading
            continue

        if section and section.startswith('Pronunciation'):
            for li in node.find_all('li'):
                accent = li.select_one('.usage-label-accent')
                accent = accent.get_text(' ', strip=True).replace(' ,', ',') if accent else ''
                for span in li.select('span.IPA'):
                    text = span.get_text().strip()
                    if text.startswith('/') or text.startswith('['):
                        ipa.append({'ipa': text, 'accent': accent})
                for player in li.find_all('audio'):
                    mp3 = player.find('source', type='audio/mpeg') or player.find('source')
                    if mp3 and mp3.get('src'):
                        src = mp3['src']
                        audio.append({'url': 'https:' + src if src.startswith('//') else src,
                                      'accent': accent or 'Audio'})

        elif section in ('Synonyms', 'Antonyms') and node.name in ('ul', 'ol', 'div'):
            nyms[section[:-1].lower()] += nym_words(node)

        elif section and section.startswith('Etymology') and node.name == 'p':
            text = html_to_text(str(node))
            if text:
                etymologies.append(text)

    return ipa, audio, etymologies, quotations, nyms['synonym'], nyms['antonym']


def unique_words(words, headword):
    """Drop repeats and the headword itself, keeping Wiktionary's order."""
    seen = {headword.lower()}
    kept = []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower())
            kept.append(w)
    return kept


ALT_FORM = re.compile(r'^(Alternative|Obsolete|Archaic) (letter-case |spelling |)(form|spelling) of', re.I)
ETYMOLOGY_STUB = re.compile(r'etymology is missing or incomplete', re.I)


def drop_alt_forms(meanings):
    kept = []
    for m in meanings:
        defs = [d for d in m['definitions'] if not ALT_FORM.match(d['text'])]
        if defs:
            kept.append({**m, 'definitions': defs})
    return kept


def save_cache(word, result):
    path = cache_path(word)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Write then rename, so another server worker never reads a half-written file.
    tmp = path.with_suffix('.tmp.{}'.format(os.getpid()))
    tmp.write_text(json.dumps(result))
    tmp.replace(path)


def add_nyms(result):
    """Fill in synonyms and antonyms for an entry cached before they were collected."""
    *_, synonyms, antonyms = get_page_details(result['title'])
    result['synonyms'] = unique_words(synonyms, result['title'])
    result['antonyms'] = unique_words(antonyms, result['title'])


def cache_path(word):
    # Bump CACHE_VERSION when the result shape changes so old entries are refetched.
    return CACHE_DIR / (CACHE_VERSION + '-' + hashlib.sha1(word.strip().encode()).hexdigest() + '.json')


@functools.lru_cache(maxsize=512)
def lookup(word):
    """Look up a word, using the on-disk cache so each word is fetched once."""
    path = cache_path(word)
    if path.exists():
        result = json.loads(path.read_text())
        if 'synonyms' not in result:
            add_nyms(result)
            save_cache(word, result)
    else:
        result = fetch_word(word)
        save_cache(word, result)

    # Ranked here rather than when fetched, so editing LITERARY_AUTHORS applies
    # to cached words too. Ties keep Wiktionary's order (oldest first).
    result['quotations'].sort(key=lambda q: literary_rank(q['author']))
    return result


def fetch_word(word):
    # 'Zeitgeist' vs 'zeitgeist', 'Babbitt' vs 'babbitt': gather every case
    # variant Wiktionary has, then skip pages that only point at another form.
    found = [(t, m) for t in candidate_titles(word) if (m := get_definitions(t))]
    if not found:
        raise WordNotFound(word)
    if len(found) > 1:
        found = [(t, drop_alt_forms(m)) for t, m in found]
        found = [(t, m) for t, m in found if m] or found[:1]

    title = found[0][0]
    meanings = [m for _, ms in found for m in ms]

    ipa, audio, etymologies, quotations, synonyms, antonyms = [], [], [], [], [], []
    for t, _ in found:
        p, a, e, q, syn, ant = get_page_details(t)
        ipa += p
        audio += a
        etymologies += [x for x in e if not ETYMOLOGY_STUB.search(x)]
        quotations += q
        synonyms += syn
        antonyms += ant
        if ipa and etymologies:
            break

    return {
        'word': word.strip().replace('_', ' '),
        'title': title,
        'source_url': PAGE_URL + quote(title.replace(' ', '_')),
        'pronunciations': ipa,
        'audio': audio,
        'etymologies': etymologies,
        'meanings': meanings,
        'quotations': quotations,
        'synonyms': unique_words(synonyms, title),
        'antonyms': unique_words(antonyms, title),
    }
