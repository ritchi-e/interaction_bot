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


def test_hindi_transliterates_english_loanwords():
    out = normalize("नमस्ते teammate, WhatsApp पर message भेजिए।", "hi")
    assert "teammate" not in out.lower()
    assert "whatsapp" not in out.lower()
    assert "message" not in out.lower()
    assert "टीममेट" in out
    assert "व्हाट्सऐप" in out
    assert "मैसेज" in out
    assert "।" not in out  # mapped to ASCII period for Indic-TTS vocab


def test_hindi_fallback_transliterates_unknown_latin():
    out = normalize("कृपया Zoom join कीजिए", "hi")
    assert "Zoom" not in out
    assert "ज़ूम" in out or "जूम" in out


def test_hindi_ages_are_cardinals_not_digits():
    out = normalize("उम्र 21 से 58 साल", "hi")
    assert "इक्कीस" in out
    assert "अट्ठावन" in out
    assert "दो एक" not in out
    # Devanagari numerals must expand the same way.
    out_deva = normalize("उम्र २१ से ५८ साल", "hi")
    assert "इक्कीस" in out_deva
    assert "अट्ठावन" in out_deva
