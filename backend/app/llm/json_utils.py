"""Parse the JSON object an LLM returns, even when it writes LaTeX inside JSON strings.

Models write `\\frac`, `\\text` or `\\neq` without escaping the backslash. json.loads then reads `\\f` as a
form feed, `\\t` as a tab and `\\n` as a newline, silently corrupting formulas ("$P(A \\text{ and } B)$"
becomes "$P(A <TAB>ext{ and } B)$"). Real newlines (`\\n` before an ordinary word) must survive.
"""

import json
import re
from typing import Any

# LaTeX commands whose first letter is also a JSON escape (b f n r t u): ambiguous, so listed by name.
_AMBIGUOUS = (
    "text|textbf|textit|times|theta|tau|tan|tanh|to|top|triangle|tilde|"
    "frac|forall|flat|"
    "neq|nu|not|ne|nabla|neg|ni|"
    "rho|right|rightarrow|rangle|rceil|rfloor|"
    "beta|bar|binom|bigcup|bigcap|bot|boldsymbol|bmod|"
    "underline|upsilon|uparrow|union"
)
_LATEX = re.compile(
    rf"(?<!\\)\\(?=(?:{_AMBIGUOUS})(?![A-Za-z]))"  # known command that collides with a JSON escape
    r"|(?<!\\)\\(?=[ac-eg-mo-qsv-zA-Z])"  # any other backslash-letter is not a JSON escape: keep it
)


def parse_json_object(raw: str) -> dict[str, Any]:
    """Best-effort: the first JSON object in the reply, with LaTeX backslashes preserved. {} if none."""
    raw = _LATEX.sub(r"\\\\", raw)
    for candidate in (raw, *re.findall(r"\{.*\}", raw, re.DOTALL)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}
