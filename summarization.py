import nltk
import re
from nltk import sent_tokenize
from nltk.corpus import stopwords
from nltk import word_tokenize
import string
import heapq
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')
stop_word = stopwords.words('portuguese')

def summarize_text(text):
    processed = text.replace(r'^\s+|\s+?$', '')
    processed = processed.replace('\n', ' ')
    processed = processed.replace("\\", '')
    processed = processed.replace(",", '')
    processed = processed.replace('"', '')
    processed = re.sub(r'\[[0-9]*\]', '', processed)

    sentences = sent_tokenize(processed)

    frequency = {}
    processed1 = processed.lower()

    for word in word_tokenize(processed1):
        if word not in stop_word and word not in string.punctuation:
            if word not in frequency.keys():
                frequency[word] = 1
            else:
                frequency[word] += 1

    max_frequency = max(frequency.values())

    for word in frequency.keys():
        frequency[word] = (frequency[word] / max_frequency)

    sentence_score = {}

    for sent in sentences:
        for word in word_tokenize(sent):
            if word in frequency.keys():
                if len(sent.split(' ')) < 30:
                    if sent not in sentence_score.keys():
                        sentence_score[sent] = frequency[word]
                    else:
                        sentence_score[sent] += frequency[word]

    summary = heapq.nlargest(5, sentence_score, key=sentence_score.get)
    return ' '.join(summary)