import requests, json, random, argparse, logging

class color:
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
    def __init__(self, word_id=None ):
        self.app_id = 'dd21b2b2'
        self.app_key = 'f64d519c73f1c17b67b74edd17317c88'
        self.language = 'en'

        self.word_id         = None
        self.sentence_list   = []
        self.definition_list = []
        self.word_raw        = {}

        if word_id is None:
            self.word_id = self.getRandomWord()
        else:
            self.word_id = word_id  


    def getRandomWord(self):
        f = open('words.out', 'r')
        line = next(f)
        for num, aline in enumerate(f):
            if random.randrange(num + 2): continue
            line = aline
        f.close()
        
        line = line.replace('\n', '')
        return line

    def printRaw(self):
        print('foo')
        print(self.word_raw)
 
    def getDefinition(self):

        word_id = self.word_id 
        app_id = self.app_id
        app_key = self.app_key
        language = self.language
        s = []

        url = 'https://od-api.oxforddictionaries.com:443/api/v1/entries/' + language + '/' + word_id.strip().lower()

        r = requests.get( url, headers = {'app_id': app_id, 'app_key': app_key} )

        word_json = json.loads( json.dumps(r.json()) )

        self.word_raw = r.text

        word = []

        for i in word_json['results']:
            for j in i['lexicalEntries']:
                for k in j['entries']:
                    if 'etymologies' in k:
                        for l in k['etymologies']:
                            word.append(color.BOLD + 'Etymology: ' + color.END  + l)
                    if 'senses' in k:
                        for l in k['senses']:
                            if 'definitions' in l:
                                for m in l['definitions']:
                                    word.append(color.BOLD + 'Definition: ' + color.END  + m)

        return word

    def lookUpWord(self):
        
        self.definition_list  = self.getDefinition()
        self.sentence_list    = self.getSentence()
       
    def printWord(self):

        word_id = self.word_id

        print( '\n' + color.BOLD + 'Word: ' + color.END + word_id.replace('_', ' ') + '\n' )
        self.printDefinition()
        print()
        self.printSentence()
        print()

    def printDefinition(self):
        for i in self.definition_list:
            print(i)

    def printSentence(self):
        for i in self.sentence_list:
            print(i)


    def getSentence(self):

        word_id = self.word_id
        app_id = self.app_id
        app_key = self.app_key
        language = self.language
        s = []


        url = 'https://od-api.oxforddictionaries.com:443/api/v1/entries/' + language + '/' + word_id.strip().lower() + '/sentences'

        r = requests.get( url, headers = {'app_id': app_id, 'app_key': app_key} )

        word_json = json.loads( json.dumps(r.json()) ) 

        for i in word_json['results']:
            for j in i['lexicalEntries']:
                for k in j['sentences']:
                    s.append( (color.BOLD + 'Sentence: ' + color.END + k['text']) )

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
        w = WordList(word)


    w.lookUpWord()
    w.printWord()

    logging.info( w.word_raw )

    print(showRaw)
    if showRaw is True:
        w.printRaw()


#########################
##
## main()
##
##############################
if __name__ == '__main__':
    main()


