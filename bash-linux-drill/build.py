#!/usr/bin/env python3
"""Join template.html + data/dayNN.json into one offline file: devops-bash-linux.html

It refuses to build when a problem marked "verified": true has not passed verify.py
(or was changed after the last verify run).

Also writes build/artifact.html: the same page without the <html>/<head>/<body>
wrapper, for publishing as a claude.ai Artifact.

Usage:  python3 build.py
"""
import datetime, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "devops-bash-linux.html"
ARTIFACT = ROOT / "build" / "artifact.html"
PLACEHOLDER = "/*__APP_DATA__*/"
MAX_BYTES = 3 * 1024 * 1024

sys.path.insert(0, str(ROOT))
from verify import problem_hash, check_rules  # noqa: E402


def main():
    files = sorted(DATA.glob("day[0-9][0-9].json"))
    if not files:
        sys.exit("No data/dayNN.json files found.")
    days = [json.loads(f.read_text()) for f in files]

    errors = check_rules(days)
    report = json.loads((DATA / "verify-report.json").read_text()) if (DATA / "verify-report.json").exists() else {}
    for d in days:
        for p in d["problems"]:
            if not p.get("verified", True):
                continue
            r = report.get(p["id"])
            if not r or r.get("status") != "pass":
                errors.append(f"{p['id']}: has not passed verify.py")
            elif r.get("hash") != problem_hash(d, p):
                errors.append(f"{p['id']}: setup or solution changed after the last verify.py run")
    if errors:
        for e in errors:
            print("BUILD FAIL:", e)
        sys.exit(f"\n{len(errors)} problems. Run: python3 verify.py   then build again.")

    payload = {"built": datetime.date.today().isoformat(), "days": days}
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # keep the JSON safe inside <script>: no "</script>" or "<!--" can appear
    text = text.replace("</", "<\\/").replace("<!--", "<\\!--")

    tpl = (ROOT / "template.html").read_text()
    if PLACEHOLDER not in tpl:
        sys.exit("template.html has no " + PLACEHOLDER + " placeholder")
    html = tpl.replace(PLACEHOLDER, text)
    OUT.write_text(html)

    # artifact version: head content (minus charset/viewport) + body content
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    head = re.sub(r'<meta charset="utf-8">\s*|<meta name="viewport"[^>]*>\s*', "", head)
    body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(head.strip() + "\n" + body.strip() + "\n")

    n_prob = sum(len(d["problems"]) for d in days)
    n_q = sum(len(d["interview"]) for d in days)
    n_unv = sum(1 for d in days for p in d["problems"] if not p.get("verified", True))
    size = OUT.stat().st_size
    print(f"Built {OUT.name}: {len(days)} days, {n_prob} problems, {n_q} interview questions, "
          f"{n_unv} not auto-verified, {size / 1024:.0f} KB")
    if size > MAX_BYTES:
        sys.exit("File is larger than 3 MB.")


if __name__ == "__main__":
    main()
