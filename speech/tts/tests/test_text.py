from text import normalize, split_clauses


def test_normalize_rupees_hindi():
    out = normalize("Price is ₹1,299 only", "hi")
    assert "रुपये" in out
    assert "₹" not in out


def test_normalize_percent_english():
    out = normalize("Get 10% off", "en")
    assert "percent" in out
    assert "%" not in out


def test_split_clauses_short_first():
    text = "Hello there my friend, how are you doing today? Fine."
    parts = split_clauses(text, first_max_words=3)
    assert parts[0] == "Hello there my"
    assert "friend" in parts[1]


def test_split_empty():
    assert split_clauses("") == []
    assert split_clauses("   ") == []
