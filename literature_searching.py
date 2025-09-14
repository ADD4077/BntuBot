from rapidfuzz import fuzz, utils

from heapq import nlargest

import json


def weighted_search(query, string, word_weight=0.7, fuzzy_weight=0.3):
    # adjust if needed
    fuzzy_ratio_threshold = 80
    query_norm = utils.default_process(query)
    string_norm = utils.default_process(string)
    query_words = set(query_norm.split())
    string_words = set(string_norm.split())
    if query_words:
        word_score = \
            sum(1 for q_word in query_words
                if any(fuzz.ratio(q_word, s_word) >= fuzzy_ratio_threshold
                    for s_word in string_words)) / len(query_words)
    else:
        word_score = 0
    fuzzy_score = fuzz.token_set_ratio(query, string) / 100
    combined_score = \
        (word_weight * word_score + fuzzy_weight * fuzzy_score) * 100
    return combined_score


def sort_search(strings: list[str], query: str, limit: int = 10):
    res = []
    for string in strings:
        res.append(
            (
                weighted_search(query, string.split("###")[0]),
                string.split("###")[1].split("%%%")[0],
                int(string.split("###")[1].split("%%%")[1])
            )
        )
    return nlargest(10, res, key=lambda x: x[0])


def search_literature(filename: str, query: str, limit: int = 10):
    with open(filename, "r", encoding="utf8") as jsonfile:
        literature = json.load(jsonfile)
    strings = []
    for group, books in literature.items():
        for i, book in enumerate(books["items"]):
            strings.append(f"{book['title']} {' '.join(book['authors'])}###{group}%%%{i}")
    results = sort_search(strings, query)
    search_results = []
    for _, group, i in results:
        search_results.append(literature[group]["items"][i])
    return search_results
