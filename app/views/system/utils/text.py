import unicodedata


def normalize_text(value):
    normalized = unicodedata.normalize('NFKD', value or '')
    text = ''.join(character for character in normalized if not unicodedata.combining(character)).casefold()
    return text.replace('đ', 'd')
