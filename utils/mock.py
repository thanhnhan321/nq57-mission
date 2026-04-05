import random

FIRSTS = ("James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda")
LASTS = ("Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis")
STREETS = ("Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Elm St", "Park Rd", "Washington Blvd")
CITIES = ("New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio")


def number(min, max):
    return random.randint(min, max)


def name():
    return f"{random.choice(FIRSTS)} {random.choice(LASTS)}"


def address():
    return f"{random.randint(1, 9999)} {random.choice(STREETS)}, {random.choice(CITIES)}"


def phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def email(full_name: str | None = None):
    return f"{(full_name or name()).replace(' ', '.').lower()}@example.com"