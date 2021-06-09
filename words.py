import requests, json, random, argparse, logging, time, random
import contextlib
import os

with open(os.devnull, 'w') as null,  contextlib.redirect_stdout(null), contextlib.redirect_stderr(null):
    from pygame import mixer

from flask import Flask, url_for, render_template
from markupsafe import escape

space = ' '
class web_color:
    PURPLE = '\n**'
    CYAN = '\n**'
    DARKCYAN = '\n**'
    BLUE = '\n**'
    GREEN = '\n**'
    YELLOW = '\n**'
    RED = '\n**'
    BOLD = '\n**'
    UNDERLINE = '\n**'
    END = '**'

class web_color:
    PURPLE = ''
    CYAN = ''
    DARKCYAN = ''
    BLUE = ''
    GREEN = ''
    YELLOW = ''
    RED = ''
    BOLD = ''
    UNDERLINE = ''
    END = ''

class term_color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class WordList():
    def __init__(self, word_id=None, web=False ):
        self.app_id = 'dd21b2b2'
        self.app_key = 'f64d519c73f1c17b67b74edd17317c88'
        self.language = 'en'

        self.word_id = None
        self.sentence_list = []
        self.audio_list = []
        self.definition_list = []
        self.word_raw = {}

        self.sentence_limit = 10

        if word_id is None:
            self.word_id = self.getRandomWord()
        else:
            self.word_id = word_id  

        if web:
            self.color = web_color
        else:
            self.color = term_color


    def getRandomWord(self):
        f = open('words.out', 'r')
        line = next(f)
        for num, aline in enumerate(f):
            if random.randrange(num + 2): continue
            line = aline
        f.close()
        
        #line = line.replace('\n', '')
        return line

    def printRaw(self):
        print(self.word_raw)
        #print(self.sentences_raw)
 
    def lookUpWord(self):
        
        self.definition_list, self.audio_list  = self.getDefinition()
        self.thesaurus_list = self.getThesaurus()
        self.sentence_list = self.getSentence()
       
    
    def printWord(self):

        word_id = self.word_id
        color = self.color

        print(color.BOLD + 'Word: ' + word_id.replace('_', ' ') + color.END )
        self.printDefinition()
        self.printThesaurus()
        self.printSentence()
        print()

    def printDefinition(self):
        for i in self.definition_list:
            print(i)


    def sayWord(self):
        for audioFile in self.audio_list:
            mp3 = requests.get(audioFile)
            tmp_mp3 = '/Users/tongeljl/Downloads/wod.mp3'
            with open(tmp_mp3, 'wb') as f:
                f.write(mp3.content)
    
            mixer.init()
            mixer.music.load(tmp_mp3)
            mixer.music.play()
            time.sleep(1.5)

    def printSentence(self):
 
        for i in self.sentence_list:
            print(i)

    def printThesaurus(self):
 
        for i in self.thesaurus_list:
            print(i)

    def getDefinition(self):

        word_id = self.word_id 
        app_id = self.app_id
        app_key = self.app_key
        language = self.language
        color = self.color

        s = []

        url = 'https://od-api.oxforddictionaries.com:443/api/v2/entries/' + language + '/' + word_id.strip().lower()

        r = requests.get( url, headers = {'app_id': app_id, 'app_key': app_key} )

        word_json = json.loads( json.dumps(r.json()) )

        self.word_raw = r.text

        word = []
        audio = []

        if 'results' in word_json:
            for results in word_json['results']:
                for lexicalEntry in results['lexicalEntries']:
                    if lexicalEntry['lexicalCategory'] is not None:
                        word.append(color.YELLOW + 'Category:' + color.END + space + lexicalEntry['lexicalCategory']['text'])
    
                    if 'entries' in lexicalEntry:
                        for entry in lexicalEntry['entries']:
                            for pronunciation in entry['pronunciations']:
                                if 'audioFile' in pronunciation:
                                    audio.append(pronunciation['audioFile'])
    
                                word.append(color.YELLOW + 'Phonetic-Spelling:' + color.END  + space + pronunciation['phoneticSpelling'])
                            if 'etymologies' in entry:
                                for l in entry['etymologies']:
                                    word.append(color.YELLOW + 'Etymology:' + color.END  + space + l)
                            if 'senses' in entry:
                                for senses in entry['senses']:
                                    if 'definitions' in senses:
                                        for definitions in senses['definitions']:
                                            word.append(color.YELLOW + 'Definition:' + color.END  + space + definitions)
                                    if 'subsenses' in senses:
                                        for subsense in senses['subsenses']:
                                            for definition in subsense['definitions']:
                                                word.append(color.YELLOW + 'Definition (subsense):' + color.END  + space + definition)

        else:
            print('No results found for ' + word_id.strip().lower() )
        return word, audio


    def getSentence(self):

        word_id = self.word_id
        app_id = self.app_id
        app_key = self.app_key
        language = self.language
        color = self.color
        s = []


        url = 'https://od-api.oxforddictionaries.com:443/api/v2/sentences/' + language + '/' + word_id.strip().lower() 

        r = requests.get( url, headers = {'app_id': app_id, 'app_key': app_key} )

        try: 
            word_json = json.loads( json.dumps(r.json()) ) 

            self.sentences_raw = r.text
            if 'results' in word_json:
                for results in word_json['results']:
                    for lexicalEntry in results['lexicalEntries']:
                        if len(lexicalEntry['sentences']) > 5:
                            sentence_len=5
                        else:
                            sentence_len=len(lexicalEntry['sentences'])

                        for sentence in random.sample(lexicalEntry['sentences'], sentence_len):
                            s.append( (color.PURPLE + 'Sentence:' + color.END + space + sentence['text']) )

        except json.decoder.JSONDecodeError:
            pass
 
        return s


    def getThesaurus(self):

        word_id = self.word_id
        app_id = self.app_id
        app_key = self.app_key
        language = self.language
        color = self.color
        s = []


        url = 'https://od-api.oxforddictionaries.com:443/api/v2/thesaurus/' + language + '/' + word_id.strip().lower() 

        r = requests.get( url, headers = {'app_id': app_id, 'app_key': app_key} )

        try: 
            word_json = json.loads( json.dumps(r.json()) ) 
            self.antonyms_raw = r.text
          
            if 'results' in word_json:
                for results in word_json['results']:
                    for lexicalEntry in results['lexicalEntries']:
                        for entry in lexicalEntry['entries']:
                            ##sense = entry['senses'][0]
                            for sense in entry['senses']:
                                if 'synonyms' in sense:
                                    if len(sense['synonyms']) > 3:
                                        synonym_len=3
                                    else:
                                        synonym_len=len(sense['synonyms'])

                                    for synonym in random.sample(sense['synonyms'], synonym_len):
                                        s.append( (color.GREEN + 'Synonym:' + color.END + space + synonym['text']) )
                                if 'antonyms' in sense:
                                    if len(sense['antonyms']) > 3:
                                        antonym_len=3
                                    else:
                                        antonym_len=len(sense['antonyms'])

                                    for antonym in random.sample(sense['antonyms'], antonym_len):
                                        s.append( (color.RED + 'Antonym:' + color.END + space + antonym['text']) )

        except json.decoder.JSONDecodeError:
            pass
 
        return s

class input_var:

    ###################
    ###
    ### Class for input variables
    ### Leave as pass and use in argument parsing
    ###
    ############################

    pass


##
## main
##
def main():

    logging.basicConfig(filename='/tmp/words.log')
    word      = None
    showRaw   = None


    parser = argparse.ArgumentParser()
    parser.add_argument('--word',          help='Word')
    parser.add_argument('--showRaw',       help='showRaw')

    args = parser.parse_args(namespace=input_var)

    if input_var.word is not None:          word    = input_var.word
    if input_var.showRaw is not None:       showRaw = input_var.showRaw

    if word is None:
        logging.info('Word input is None')
    else:
        logging.info('Word input is: ' + word)

    if word is None:
        w = WordList()
    else:
        w = WordList(word, False)


    if showRaw:
        w.printRaw()
    
    w.lookUpWord()
    w.printWord()
    #w.sayWord()

    logging.info( w.word_raw )



#########################
##
## main()
##
##############################
if __name__ == '__main__':
    main()


