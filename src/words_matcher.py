import openpyxl
from fuzzywuzzy import process
from typing import List

FUZZY_THRESHOLD = 80


def _load_dict_words(dict_path: str) -> List[str]:
    """Read all non-empty string values from all sheets and columns."""
    wb = openpyxl.load_workbook(dict_path, data_only=True)
    words = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell and isinstance(cell, str) and cell.strip():
                    words.append(cell.strip())
    return words


def match_words(product_words: List[str], dict_path: str) -> List[str]:
    """
    For each word in product_words, find matching words in the dictionary file.
    Returns only words from the dictionary (original spelling), deduplicated.
    Threshold: fuzzywuzzy score >= 80.
    """
    if not product_words:
        return []

    dict_words = _load_dict_words(dict_path)
    if not dict_words:
        return []

    matched = set()
    for word in product_words:
        results = process.extractBests(word, dict_words, score_cutoff=FUZZY_THRESHOLD)
        for match_word, _score in results:
            matched.add(match_word)

    return list(matched)
