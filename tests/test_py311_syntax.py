"""The workflows run Python 3.11 while local interpreters are newer. PEP 701
(3.12) allows a backslash, a comment or a reused quote inside an f-string
replacement field; 3.11 raises SyntaxError at import and the hourly job
publishes nothing (2026-09-23 20:09Z, run 35914050749). This scan makes the
local ritual catch it before a push."""
import io
import tokenize
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ["forecast", "tests", "history/scripts", "audits", "scripts"]


def pep701_violations(source, path=""):
    out = []
    if not hasattr(tokenize, "FSTRING_START"):      # pre-3.12: the interpreter itself enforces the rule
        return out
    toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    stack = []                                   # per open f-string: [quote, brace depth]
    for t in toks:
        if t.type == tokenize.FSTRING_START:
            q = t.string.lstrip("fFrRbB")
            if stack and stack[-1][1] > 0 and q == stack[-1][0]:
                out.append(f"{path}:{t.start[0]}: nested f-string reuses the outer quote {q!r}")
            stack.append([q, 0])
            continue
        if t.type == tokenize.FSTRING_END:
            stack.pop()
            continue
        if not stack:
            continue
        top = stack[-1]
        if t.type == tokenize.OP and t.string == "{":
            top[1] += 1
        elif t.type == tokenize.OP and t.string == "}":
            top[1] -= 1
        elif top[1] > 0 and t.type in (tokenize.STRING, tokenize.FSTRING_MIDDLE) and "\\" in t.string:
            out.append(f"{path}:{t.start[0]}: backslash inside an f-string replacement field")
        elif top[1] > 0 and t.type == tokenize.COMMENT:
            out.append(f"{path}:{t.start[0]}: comment inside an f-string replacement field")
        elif (top[1] > 0 and t.type == tokenize.STRING and top[0] not in ('"""', "'''")
              and t.string.lstrip("rRbBuU")[:1] == top[0][:1]):
            out.append(f"{path}:{t.start[0]}: string in a replacement field reuses the outer quote")
    return out


class Py311SyntaxTests(unittest.TestCase):
    def test_scanner_flags_the_construct_that_broke_the_hourly_job(self):
        if not hasattr(tokenize, "FSTRING_START"):
            self.skipTest("pre-3.12 tokenizer: no f-string tokens to scan")
        bad = ('html = f"""<h3>{("<span class=\\"note\\">x</span>" % 1) if d else ""}</h3>"""\n')
        self.assertTrue(pep701_violations(bad))
        good = ('note = "x"\nhtml = f"""<h3>{note}</h3> {d[\'a\']} {"a" if d else "b"} \\u2014"""\n')
        self.assertEqual(pep701_violations(good), [])

    def test_repo_python_has_no_pep701_only_fstrings(self):
        if not hasattr(tokenize, "FSTRING_START"):
            self.skipTest("pre-3.12 tokenizer: the interpreter itself enforces the rule")
        found = []
        for d in SCAN:
            for p in sorted((ROOT / d).rglob("*.py")) if (ROOT / d).exists() else []:
                found += pep701_violations(p.read_text(), str(p.relative_to(ROOT)))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
