from flask import Flask, url_for, render_template
from markupsafe import escape
import words

app = Flask(__name__)


@app.route('/')
def main():
    return 'Hello Word'
@app.route('/word')
def word():
    wordlist = words.WordList(web=True)
    definition, audio  = wordlist.getDefinition()
    thesaurus = wordlist.getThesaurus()
    sentences = wordlist.getSentence()
    return render_template('word.html', word=wordlist.word_id, define=definition, thes=thesaurus, sent=sentences, aud=audio)

@app.route('/<myword>')
def user_word(myword):
    wordlist = words.WordList(myword, True)
    definition, audio  = wordlist.getDefinition()
    thesaurus = wordlist.getThesaurus()
    sentences = wordlist.getSentence()
    return render_template('word.html', word=wordlist.word_id, define=definition, thes=thesaurus, sent=sentences, aud=audio)
