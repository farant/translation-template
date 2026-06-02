"""Structural parity check between an EN HTML file and its LA counterpart.

Checks matching counts of <p>, <hr />, <em>, anchor ids, and that every
<p> carries a data-page attribute (the proofreading anchor)."""
import re
import sys
from pathlib import Path


def count_tags(html):
    return {
        "p": len(re.findall(r"<p\b", html)),
        "hr": len(re.findall(r"<hr\b", html)),
        "em": len(re.findall(r"<em\b", html)),
        "data_page": len(re.findall(r"data-page=", html)),
        "ids": set(re.findall(r'<p id="([^"]+)"', html)),
    }


def verify_pair(en_path, la_path):
    """Return (ok, problems). ok is True iff no problems found."""
    en = count_tags(Path(en_path).read_text(encoding="utf-8"))
    la = count_tags(Path(la_path).read_text(encoding="utf-8"))
    problems = []
    for key in ("p", "hr", "em"):
        if en[key] != la[key]:
            problems.append(f"<{key}> count differs: EN={en[key]} LA={la[key]}")
    if en["ids"] != la["ids"]:
        problems.append(f"anchor ids differ: EN-only={en['ids'] - la['ids']} "
                        f"LA-only={la['ids'] - en['ids']}")
    for label, counts in (("EN", en), ("LA", la)):
        if counts["data_page"] != counts["p"]:
            problems.append(
                f"{label}: {counts['p'] - counts['data_page']} <p> missing data-page")
    return (not problems), problems


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m scripts.verify <english.html> <latin.html>")
        sys.exit(1)
    ok, problems = verify_pair(sys.argv[1], sys.argv[2])
    if ok:
        print("PASS")
    else:
        print("FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)
