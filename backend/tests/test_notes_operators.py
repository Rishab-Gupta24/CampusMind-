"""Lecture notes: probability operators written as words inside LaTeX become symbols."""

from app.ingest.lecture_notes import symbol_operators


def test_words_become_symbols():
    raw = r"P(A \text{ given } B) = \frac{P(A \text{ and } B)}{P(B)}"
    assert symbol_operators(raw) == r"P(A \mid B) = \frac{P(A \cap B)}{P(B)}"


def test_mathrm_or():
    assert symbol_operators(r"P(A \mathrm{or} B)") == r"P(A \cup B)"


def test_prose_untouched():
    text = "The probability of A and B is given here, or not."
    assert symbol_operators(text) == text
