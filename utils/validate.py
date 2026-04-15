import re

def isfloat(value: str):
    return bool(re.match(r'^[-+]?[0-9]*\.?[0-9]+$', value))