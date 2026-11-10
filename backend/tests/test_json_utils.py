from app.llm.json_utils import parse_json_object

BS = chr(92)  # one backslash, written this way so no editor or shell can turn it into an escape


def test_latex_survives_json_parsing() -> None:
    raw = '{"s": "$P(A ' + BS + "text{ and } B) = " + BS + "frac{1}{2}, x " + BS + "neq y, " + BS + 'cdot z$"}'
    assert parse_json_object(raw)["s"] == (
        "$P(A " + BS + "text{ and } B) = " + BS + "frac{1}{2}, x " + BS + "neq y, " + BS + "cdot z$"
    )


def test_real_newlines_are_kept() -> None:
    raw = '{"summary": "Line one.' + BS + "nThe second line." + BS + 'nNext"}'
    assert parse_json_object(raw)["summary"] == "Line one.\nThe second line.\nNext"


def test_object_inside_extra_text_and_garbage() -> None:
    assert parse_json_object('Sure! {"a": 1} hope that helps') == {"a": 1}
    assert parse_json_object("not json") == {}
    assert parse_json_object("[1, 2]") == {}
