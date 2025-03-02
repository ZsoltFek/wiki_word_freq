from flask import Flask, request, jsonify
import wikipediaapi
from collections import Counter
import re
import numpy as nps

app = Flask(__name__)
wiki = wikipediaapi.Wikipedia('en')

def clean_text(text):
    """
    Remove punctuation from text body.
    Unhandled edgecases: "Watt" (person) and "watt" (SI unit of power).
    The complexity of the prevention of this edgecase deems the fix out-of-scope.

    Potential edgecase: compound words.
    "high-speed" makes sense to keep as one word
    "420-watt" not so much
    The scope of this filter's logic is not clearly defined in the task, so I am only noting it here.
    """
    text = re.sub(r'(?<!\d)\.(?!\d)', '', text)  # Remove . not between numbers
    text = re.sub(r'(?<!\w)-(?!\w)', '', text)  # Remove - not between alphanumeric characters
    text = re.sub(r'[^A-Za-z0-9.\s-]', '', text)  # Allow letters, numbers, spaces, periods, and hyphens
    words = text.lower().split()
    return words

def get_word_frequencies(title, depth, visited=None):
    """
    Returns counter of found words in page. 
    Calls itself if there are links found and depth is not at the end yet.

    :param title: string, title of the article currently processed
    :param depth: int, remaining levels to process
    :return: dict, appearance count for each word
    """
    if visited is None:
        visited = set()
    if title in visited or depth < 0:
        return Counter()
    
    visited.add(title)
    page = wiki.page(title)
    
    if not page.exists():
        return Counter()
    
    word_freq = Counter(clean_text(page.text))
    
    if depth > 0:
        for link in page.links.keys():
            word_freq += get_word_frequencies(link, depth - 1, visited)
    
    return word_freq

@app.route('/word_frequency', methods=['GET'])
def get_word_frequencies_route():
    """
    GET method to query word frequencies.
    Request includes:
    title: String, exact title of wikipedia article.
    depth: Integer, how deep to go from origin, through wikipedia links in page.

    Return: dictionary with both count and percentage.
    """
    title = request.args.get('title','')
    depth = request.args.get('depth', default=0, type=int)
    
    if not title:
        return jsonify({'error': 'Title parameter is required'}), 400
    if not isinstance(depth, int) or depth < 0:
        return jsonify({'error': 'Depth must be a non-negative integer'}), 400
    
    word_freq = get_word_frequencies(title, depth)
    total_words = sum(word_freq.values())
    
    word_freq_percentage = {
        word: {
            "count": count,
            "percentage": (count / total_words) * 100 if total_words > 0 else 0
        } for word, count in word_freq.items()
    }
    
    return jsonify(word_freq_percentage)

@app.route('/keywords', methods=['POST'])
def post_word_frequencies_route():
    """
    POST method to query word frequencies.
    Request includes:
    title: String, exact title of wikipedia article.
    depth: Integer, how deep to go from origin, through wikipedia links in page.
    ignore_list: Set, what words to ignore in the result.
    percentile: Integer, limits how frequent words we return

    Return: dictionary with both appearance count and percentage.
    """
    data = request.get_json()
    title = data.get('title', '')
    depth = data.get('depth', 0)
    ignore_list = set(data.get('ignore_list', []))
    percentile = data.get('percentile', 0)
    
    if not title:
        return jsonify({'error': 'Title parameter is required'}), 400
    if not isinstance(depth, int) or depth < 0:
        return jsonify({'error': 'Depth must be a non-negative integer'}), 400
    if not isinstance(percentile, (int, float)) or not (0 <= percentile <= 100):
        return jsonify({'error': 'Percentile must be a number between 0 and 100'}), 400
    
    word_freq = get_word_frequencies(title, depth)
    
    for word in ignore_list:
        if word in word_freq:
            del word_freq[word]
    
    if percentile > 0:
        freq_values = np.array(list(word_freq.values()))
        threshold = np.percentile(freq_values, percentile)
        word_freq = {word: count for word, count in word_freq.items() if count >= threshold}
    
    total_words = sum(word_freq.values())
    
    word_freq_percentage = {
        word: {
            "count": count,
            "percentage": (count / total_words) * 100 if total_words > 0 else 0
        } for word, count in word_freq.items()
    }
    
    return jsonify(word_freq_percentage)



"""
Notes:

clean_text can be change and optimized based on requirements.
Currently, numbers and letters, hyphen and period separated are all shown.
This goes into the "what is a word" question. As alluded to in the function comment, 420-watt and high-speed are both counted as singular words here.
As my experience and career is in software development and not linguistics or philosophy, I felt it best to leave this like this but make a note of the behaviour.

ignore_list could be handled multiple ways, it wasn't clear for me which was wanted here.
Currently, the words in the ignore list are deleted and only after that is percentile calculated, on the remaining words and counts.
Another way of handling could be that percentages are calculated first and ignore_list only comes into play afterwards.
It comes down to the quesion of 'do we want to ignore part of the input or part of the output'. The current implementation does the former.
To implement the latter, we need to swap lines 108-110 and 112-115.

One last note about ignore_list: while in the task it was mentioned as "ignore_list (array[string]): A list of words to ignore.", I took the initiative to make it a set.
I believe a set type is more clear in this usecase as there is no reason for a word appearing multiple times in ignore_list,
and if we'd want to check if a word is inside the ignore_list, set is better in performance.

"""