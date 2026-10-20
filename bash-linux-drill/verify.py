#!/usr/bin/env python3
"""Run every solution in a clean sandbox and record the REAL output.

For each problem with "verified": true:
  1. make a fresh, empty temp folder and use it as HOME
  2. run the day's `setup` with bash
  3. run the problem's `solution` with bash, from ~/bash-practice/dayNN/<workdir>,
     inside a pseudo-terminal (so `ls` prints columns like a real terminal)
  4. check the exit code, and write the output into the JSON as `expected_output`

Then a second pass runs all problems of a day in order, in one sandbox (like the
learner does). Problems with "output_check": true must give the same output again,
or the run fails (their output is not stable enough for the "Check my output" box).

It also checks the content rules (time budget, ids, hints, coverage ...).
A report is written to data/verify-report.json; build.py refuses to build when a
verified problem has not passed.

Usage:
  python3 verify.py              # all days
  python3 verify.py 3 4          # only day 3 and day 4
  python3 verify.py --check-only # only the content rules, no running
"""
import hashlib, json, os, pathlib, pty, pwd, re, select, shlex, shutil, signal, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORT = DATA / "verify-report.json"
SHOWN_HOME = "/home/wicky"          # temp HOME is shown as this path in the output
TIMEOUT = 40                        # seconds per script
WARMUP, INTERVIEW, RECAP, LIMIT = 8, 7, 5, 90
TYPES = {"command", "fix-bug", "predict", "explain-error", "convert", "incident", "script", "concept"}
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][0-9A-Za-z]|\x1b[=>]")


def code(v):
    return "\n".join(v) if isinstance(v, list) else (v or "")


def problem_hash(day, p):
    raw = code(day["setup"]) + "\0" + solution_script(p) + "\0" + p.get("workdir", ".") + "\0" + json.dumps(p.get("checks", []))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# New-style problems have "steps" (each with its own real output) and optional "files"
# (the correct scripts). A step with "edit": NAME stands for "open NAME in an editor and make it
# like the correct script": verify.py writes the file at that point. "run": false = not executed.
STEP_MARK = "@@STEP {}@@"


def solution_script(p):
    if "steps" not in p:
        return code(p.get("solution"))
    files = {f["name"]: code(f["content"]) for f in p.get("files", [])}
    parts = []
    for i, s in enumerate(p["steps"]):
        parts.append(f"printf '%s\\n' '{STEP_MARK.format(i)}'")
        if s.get("edit"):
            parts.append(f"cat > {shlex.quote(s['edit'])} <<'__VERIFY_FILE_END__'\n{files[s['edit']]}\n__VERIFY_FILE_END__")
        if s.get("run", True) and s.get("code"):
            parts.append(code(s["code"]))
    return "\n".join(parts)


def split_steps(out, p):
    """Return (combined output, list of per-step outputs or None)."""
    if "steps" not in p:
        return out, None
    chunks, cur = {}, None
    for line in out.split("\n"):
        m = re.fullmatch(r"@@STEP (\d+)@@", line)
        if m:
            cur = int(m.group(1))
            chunks[cur] = []
        elif cur is not None:
            chunks[cur].append(line)
    step_outs = ["\n".join(chunks.get(i, [])).strip("\n") for i in range(len(p["steps"]))]
    return "\n".join(o for o in step_outs if o), step_outs


# ---------------------------------------------------------------- running

def run_user():
    """Run as the current user, or as 'wicky' when we are root (root ignores permissions)."""
    if os.geteuid() != 0:
        return None
    try:
        return pwd.getpwnam("wicky")
    except KeyError:
        sys.exit("verify.py runs as root. Create a normal sandbox user first:  useradd -m -s /bin/bash wicky")


def sandbox_env(home, user):
    name = user.pw_name if user else pwd.getpwuid(os.getuid()).pw_name
    return {
        "HOME": home, "USER": name, "LOGNAME": name, "SHELL": "/bin/bash",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8", "TERM": "xterm-256color", "TZ": "Asia/Colombo",
    }   # no COLUMNS: an interactive bash does not export it, and ps would cut long lines


def demote(user):
    if not user:
        return lambda: None

    def fn():
        os.setgid(user.pw_gid)
        os.initgroups(user.pw_name, user.pw_gid)
        os.setuid(user.pw_uid)
    return fn


def run_script(script_path, cwd, env, user):
    """Run `bash script` in a pseudo-terminal. Returns (exit_code, output, timed_out)."""
    master, slave = pty.openpty()
    try:
        import fcntl, struct, termios
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    except Exception:
        pass
    pre = demote(user)

    def child_setup():
        os.setsid()
        pre()

    proc = subprocess.Popen(["bash", script_path], cwd=cwd, env=env, stdin=slave, stdout=slave,
                            stderr=slave, preexec_fn=child_setup, close_fds=True)
    os.close(slave)
    chunks, deadline, timed_out = [], time.time() + TIMEOUT, False
    while True:
        if time.time() > deadline:
            timed_out = True
            break
        r, _, _ = select.select([master], [], [], 0.2)
        if r:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        elif proc.poll() is not None:
            # main script ended; read what is left, do not wait for background jobs
            while True:
                r, _, _ = select.select([master], [], [], 0.3)
                if not r:
                    break
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:
                    break
                chunks.append(data)
            break
    try:
        os.killpg(proc.pid, signal.SIGKILL)   # also stops background jobs the script started
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    os.close(master)
    out = b"".join(chunks).decode("utf-8", "replace")
    return (proc.returncode if not timed_out else 124), out, timed_out


def clean_output(out, home, script_names):
    out = out.replace("\r\n", "\n").replace("\r", "")
    out = ANSI.sub("", out)
    out = out.replace(home, SHOWN_HOME)
    # an error inside the solution file looks like "/tmp/x/solution.sh: line 3: cd: ..."
    # in a terminal the user sees "bash: cd: ...", so show it like that
    for name in script_names:
        out = re.sub(r"(?m)^\S*" + re.escape(name) + r": line \d+: ", "bash: ", out)
        out = re.sub(r"(?m)^\S*/" + re.escape(name) + r": ", "bash: ", out)
    lines = [ln.rstrip() for ln in out.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


class Sandbox:
    def __init__(self, user):
        self.user = user
        self.home = tempfile.mkdtemp(prefix="bp-home-")
        self.scripts = tempfile.mkdtemp(prefix="bp-scripts-")
        os.chmod(self.scripts, 0o755)
        if user:
            os.chown(self.home, user.pw_uid, user.pw_gid)
        os.chmod(self.home, 0o755)
        self.env = sandbox_env(self.home, user)

    def run(self, name, text, cwd):
        path = os.path.join(self.scripts, name)
        with open(path, "w") as f:
            f.write(text + "\n")
        os.chmod(path, 0o644)
        rc, out, to = run_script(path, cwd, self.env, self.user)
        return rc, clean_output(out, self.home, [name]), to

    def close(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.scripts, ignore_errors=True)


def day_dir(sb, day):
    return os.path.join(sb.home, "bash-practice", f"day{day['day']:02d}")


def run_problem(sb, day, p):
    cwd = os.path.normpath(os.path.join(day_dir(sb, day), p.get("workdir", ".")))
    if not os.path.isdir(cwd):
        return 1, f"[verify] workdir does not exist after setup: {cwd}", False
    return sb.run(f"{p['id']}.sh", solution_script(p), cwd)


def run_setup(sb, day):
    return sb.run("setup.sh", code(day["setup"]), sb.home)


# ---------------------------------------------------------------- content rules

def check_rules(days):
    errors, seen = [], {}
    for d in days:
        n = d["day"]
        tag = f"day{n:02d}"
        for k in ("day", "week", "title", "goal", "setup", "reset", "warmup", "problems", "interview", "recap", "coverage"):
            if k not in d:
                errors.append(f"{tag}: missing field '{k}'")
        for p in d.get("problems", []):
            if "\t" in solution_script(p):
                errors.append(f"{p.get('id')}: solution, steps or files have a TAB character; use spaces")
        if "\t" in code(d.get("setup")):
            errors.append(f"{tag}: setup has a TAB character (pasting it in a terminal triggers completion); use printf '\\t'")
        if f"bash-practice/day{n:02d}" not in code(d.get("reset")):
            errors.append(f"{tag}: reset must only touch ~/bash-practice/day{n:02d}")
        timed = [p for p in d["problems"] if not p.get("optional")]
        if not 4 <= len(timed) <= 6:
            errors.append(f"{tag}: has {len(timed)} timed problems (must be 4-6)")
        total = WARMUP + sum(p["minutes"] for p in timed) + d.get("interview_minutes", INTERVIEW) + RECAP
        if total > LIMIT:
            errors.append(f"{tag}: day time is {total} min (limit {LIMIT})")
        if not any(p.get("type") == "fix-bug" for p in d["problems"]):
            errors.append(f"{tag}: needs at least one 'fix-bug' problem")
        if any(p.get("steps") for p in d["problems"]) and not any(p.get("type") == "script" and not p.get("optional") for p in d["problems"]):
            errors.append(f"{tag}: teaching-style days need at least one timed 'script' problem (write a script)")
        ids = {p["id"] for p in d["problems"]}
        for c in d.get("cards", []):
            if not re.fullmatch(rf"d{n:02d}c\d\d", c.get("id", "")):
                errors.append(f"{tag}: card id must look like d{n:02d}cNN (has {c.get('id')})")
            if c.get("id") in seen:
                errors.append(f"{c.get('id')}: duplicate card id")
            seen[c.get("id")] = n
            for k in ("q", "a", "what", "topic"):
                if not c.get(k):
                    errors.append(f"{c.get('id')}: card needs '{k}'")
            for pid in c.get("links", []):
                if pid not in ids:
                    errors.append(f"{c.get('id')}: card links to unknown problem {pid}")
            if "\t" in code(c.get("example", "")):
                errors.append(f"{c.get('id')}: card example has a TAB character")
        if not 3 <= len(d.get("warmup", [])) <= 4:
            errors.append(f"{tag}: warm-up must have 3-4 questions")
        if len(d.get("interview", [])) < 5:
            errors.append(f"{tag}: interview round needs at least 5 questions")
        for p in d["problems"]:
            pid = p.get("id", "?")
            if pid in seen:
                errors.append(f"{pid}: duplicate id (also in day{seen[pid]:02d})")
            seen[pid] = n
            if not re.fullmatch(rf"d{n:02d}p\d\d", pid):
                errors.append(f"{pid}: id must look like d{n:02d}pNN")
            for k in ("title", "type", "topic", "minutes", "situation", "task", "hints",
                      "explanation", "mistakes", "interview_say", "try_yourself"):
                if not p.get(k):
                    errors.append(f"{pid}: missing or empty '{k}'")
            if not p.get("solution") and not p.get("steps"):
                errors.append(f"{pid}: needs 'solution' or 'steps'")
            if p.get("steps"):
                if not p.get("learn"):
                    errors.append(f"{pid}: step-style problems need a 'learn' lesson")
                names = {f["name"] for f in p.get("files", [])}
                for s in p["steps"]:
                    if not s.get("say"):
                        errors.append(f"{pid}: every step needs 'say' (the explanation)")
                    if s.get("edit") and s["edit"] not in names:
                        errors.append(f"{pid}: step edits unknown file {s['edit']}")
                if p.get("type") in ("fix-bug", "script") and not p.get("spec"):
                    errors.append(f"{pid}: script and fix-bug problems need 'spec' (what the script must do)")
            if p.get("type") not in TYPES:
                errors.append(f"{pid}: unknown type '{p.get('type')}'")
            if len(p.get("hints", [])) != 3:
                errors.append(f"{pid}: needs exactly 3 hints")
            if not p.get("optional") and not 10 <= p.get("minutes", 0) <= 15:
                errors.append(f"{pid}: timed problems take 10-15 minutes (has {p.get('minutes')})")
            if not p.get("verified", True):
                if not p.get("typical_output"):
                    errors.append(f"{pid}: verified=false needs 'typical_output'")
                if p.get("output_check"):
                    errors.append(f"{pid}: verified=false cannot use output_check")
            if not 1 <= len(p.get("mistakes", [])) <= 3:
                errors.append(f"{pid}: needs 1-3 mistakes")
        texts = [w.get(k, "") for w in d.get("warmup", []) + d.get("interview", []) for k in ("q", "a")]
        for p in d["problems"]:
            texts += [p.get("situation", ""), p.get("interview_say", ""), p.get("try_yourself", ""), p.get("output_note", "")]
            texts += p.get("task", []) + p.get("hints", []) + p.get("mistakes", [])
            texts += [e.get("meaning", "") for e in p.get("explanation", [])]
            texts += p.get("outcomes", []) + p.get("spec", [])
            texts += [s.get("say", "") for s in p.get("steps", [])] + [f.get("say", "") for f in p.get("files", [])]
            for sec in p.get("learn", []):
                tx = sec.get("text", [])
                texts += ([tx] if isinstance(tx, str) else tx) + [sec.get("title", "")]
        for c in d.get("cards", []):
            texts += [c.get("q", ""), c.get("what", ""), c.get("does", "")] + [f[1] for f in c.get("flags", [])]
        for s in texts:
            if s.count("`") % 2:
                errors.append(f"{tag}: odd number of backticks (broken `code` marks) in: {s[:70]}")
        for c in d.get("coverage", []):
            for pid in c["problems"]:
                if pid not in {p["id"] for p in d["problems"]}:
                    errors.append(f"{tag}: coverage item '{c['item']}' points to unknown problem {pid}")
    return errors


def crash_plan(days):
    """Same rule as the app: core problems in day order, max 6 per day, max 70 problem minutes."""
    budget = LIMIT - WARMUP - INTERVIEW - RECAP
    plan, cur, mins = [], [], 0
    for d in days:
        for p in d["problems"]:
            if not p.get("core"):
                continue
            if cur and (mins + p["minutes"] > budget or len(cur) >= 6):
                plan.append(cur)
                cur, mins = [], 0
            cur.append(p)
            mins += p["minutes"]
    if cur:
        plan.append(cur)
    return plan


# ---------------------------------------------------------------- main

def main(argv):
    check_only = "--check-only" in argv
    wanted = {int(a) for a in argv if a.isdigit()}
    files = sorted(DATA.glob("day[0-9][0-9].json"))
    days = [json.loads(f.read_text()) for f in files]
    errors = check_rules(days)
    for e in errors:
        print("RULE FAIL:", e)

    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    results = []
    if not check_only:
        user = run_user()
        for f, d in zip(files, days):
            if wanted and d["day"] not in wanted:
                continue
            changed = False
            fresh = {}
            for p in d["problems"]:
                if not p.get("verified", True):
                    results.append((p["id"], "SKIP", "not auto-verified (typical output)"))
                    report[p["id"]] = {"status": "skip", "hash": problem_hash(d, p)}
                    continue
                sb = Sandbox(user)
                try:
                    rc, out, _ = run_setup(sb, d)
                    if rc != 0:
                        results.append((p["id"], "FAIL", f"setup exit {rc}: {out[-300:]}"))
                        report[p["id"]] = {"status": "fail", "hash": problem_hash(d, p)}
                        continue
                    rc, out, to = run_problem(sb, d, p)
                finally:
                    sb.close()
                out, step_outs = split_steps(out, p)
                if step_outs is not None:
                    for s, so in zip(p["steps"], step_outs):
                        if s.get("run", True):
                            if s.get("out") != so:
                                s["out"] = so
                                changed = True
                        elif "out" in s:
                            del s["out"]
                            changed = True
                want = p.get("expect_exit", 0)
                fresh[p["id"]] = out
                if to:
                    status, note = "FAIL", f"timeout after {TIMEOUT}s"
                elif rc != want:
                    status, note = "FAIL", f"exit {rc}, expected {want}. Last output: {out[-400:]!r}"
                elif "bp-home-" in out or "bp-scripts-" in out:
                    status, note = "FAIL", "output shows a sandbox temp path (bp-home-/bp-scripts-); print a path the learner would see"
                else:
                    status, note = "PASS", f"exit {rc}, {len(out.splitlines())} lines"
                    if p.get("expected_output") != out:
                        p["expected_output"] = out
                        changed = True
                # "checks": prove that the error texts in "mistakes" are real
                for i, c in enumerate(p.get("checks", [])):
                    sb = Sandbox(user)
                    try:
                        run_setup(sb, d)
                        cwd = os.path.normpath(os.path.join(day_dir(sb, d), c.get("workdir", p.get("workdir", "."))))
                        _, cout, _ = sb.run(f"{p['id']}-check{i}.sh", c["run"], cwd)
                    finally:
                        sb.close()
                    if c["expect"] not in cout:
                        status, note = "FAIL", f"mistake check {i}: expected text {c['expect']!r} not in output {cout[-300:]!r}"
                results.append((p["id"], status, note))
                report[p["id"]] = {"status": status.lower(), "hash": problem_hash(d, p)}

            # second pass: the whole day in order, in one sandbox, like the learner
            sb = Sandbox(user)
            try:
                rc, out, _ = run_setup(sb, d)
                for p in d["problems"]:
                    if not p.get("verified", True) or p["id"] not in fresh:
                        continue
                    rc, out, _ = run_problem(sb, d, p)
                    out, _ = split_steps(out, p)
                    if out != fresh[p["id"]]:
                        if p.get("output_check"):
                            results.append((p["id"], "FAIL", "output is different when the day is done in order "
                                            "(or not stable). Fix the problem or set output_check=false"))
                            report[p["id"]]["status"] = "fail"
                        else:
                            results.append((p["id"], "NOTE", "output differs in the in-order run (output_check is off)"))
            finally:
                sb.close()
            if changed:
                f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    REPORT.write_text(json.dumps(dict(sorted(report.items())), indent=1) + "\n")

    if results:
        print(f"\n{'PROBLEM':<10} {'RESULT':<6} DETAILS")
        print("-" * 78)
        for pid, status, note in results:
            print(f"{pid:<10} {status:<6} {note[:200]}")
    fails = [r for r in results if r[1] == "FAIL"]

    print("\nDay time budget (warm-up 8 + timed problems + interview 7 (or interview_minutes) + recap 5):")
    for d in days:
        timed = [p for p in d["problems"] if not p.get("optional")]
        extra = [p for p in d["problems"] if p.get("optional")]
        total = WARMUP + sum(p["minutes"] for p in timed) + d.get("interview_minutes", INTERVIEW) + RECAP
        print(f"  day{d['day']:02d}: {len(timed)} timed + {len(extra)} extra, {total} min"
              f"{'  <-- OVER LIMIT' if total > LIMIT else ''}")
    plan = crash_plan(days)
    core = sum(len(c) for c in plan)
    print(f"\nCrash week: {core} core problems in {len(plan)} days "
          + ", ".join(f"{len(c)}p/{WARMUP + INTERVIEW + RECAP + sum(p['minutes'] for p in c)}m" for c in plan))
    skipped = [p["id"] for d in days for p in d["problems"] if not p.get("verified", True)]
    print(f"Not auto-verified ({len(skipped)}): {', '.join(skipped) or 'none'}")

    if errors or fails:
        print(f"\nFAILED: {len(errors)} rule errors, {len(fails)} failing problems.")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
