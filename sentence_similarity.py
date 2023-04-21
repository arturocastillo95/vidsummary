import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download('punkt')
nltk.download('stopwords')

def preprocess_text(text):
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import PorterStemmer

    stop_words = set(stopwords.words('english'))
    stemmer = PorterStemmer()

    tokens = word_tokenize(text)
    tokens = [token.lower() for token in tokens if token.isalnum()]
    tokens = [stemmer.stem(token) for token in tokens if token not in stop_words]

    return ' '.join(tokens)

def sentence_similarity(sentence1, sentence2, threshold=0.6):
    processed_sentence1 = preprocess_text(sentence1)
    processed_sentence2 = preprocess_text(sentence2)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([processed_sentence1, processed_sentence2])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])

    return similarity

def similar_sentences(sentence1, sentence2, threshold=0.6):
    similarity = sentence_similarity(sentence1, sentence2)
    if similarity >= threshold:
        return sentence2
    else:
        return None
