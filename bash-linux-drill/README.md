# Bash & Linux Drill (DevOps Associate interview trainer)

A 28-day, hands-on Bash and Linux trainer for Pasindu. One HTML file, works offline.
Every day is **90 minutes at most**: warm-up recall, 4-6 timed problems, an interview round, and a recap.

| | |
|---|---|
| Days | 28 (4 weeks; days 7, 14, 21, 28 are review days) |
| Problems | 190 (140 timed + 50 optional extras) |
| "Find the bug" problems | 28 (at least one every day) |
| Interview questions | 182 (Day 28: 30 rapid-fire + 6 troubleshooting scenarios) |
| Cheat-sheet rows | 324 (built from the day recaps) |
| Crash week | 35 core problems in 7 days |
| Auto-verified | 184 of 190 problems (6 show "Typical output", see below) |

## Open the app

1. Download `devops-bash-linux.html`.
2. Double-click it. It opens in your browser. No internet is needed.
3. Progress is saved in the browser. Use **Progress → Export progress** once a week to keep a backup file.

From WSL you can copy it to the Windows desktop:

```bash
cp devops-bash-linux.html /mnt/c/Users/<your-windows-name>/Desktop/
```

## How to use it every day

1. Open the day in the left list. Press **Start day**. The timer shows the time spent and the time left of the 90 minutes.
2. Copy the **Setup** block into the Ubuntu (WSL) terminal. It creates `~/bash-practice/dayNN/`.
3. Do the **Warm-up recall** (8 min). Answer in your head first, then press *Show answer*.
4. Do the timed **Problems**. Open one, read the situation, try it in the terminal, use the hints one by one,
   then open **Show real-world answer**. Mark **Done**, or **I forgot this** to send it to the Review queue.
   Paste your terminal output into **Check my output** when the box is there.
5. Do the **Interview round** out loud (7 min; 20 min on Day 28).
6. Read the **Day recap** and press **Mark day complete**. The day's problems come back for review after 1, 3, 7 and 14 days.
7. Every day: press **Review → Start 10-minute review** (6-8 due items).

Extras are optional and are **not** counted in the 90 minutes.

**Time alerts.** Each open problem has its own clock. The app shows a small message when 2 minutes are left,
a popup when the planned time is finished (with "Show next hint" and "Show the answer"), and a second popup
at 1.5 times the planned time. The day clock shows a popup at 80 minutes and at 90 minutes.
A short beep plays with each alert; turn it off with **Sound** in the day timer.

**Teaching answers.** Problems are being moved to a teaching format: **Learn first (theory)** opens a short lesson
with diagrams in simple English, and **Show real-world answer** shows the lesson, the correct script with long
comments, then every step with the reason and its real output. Every day in this format has at least one
"Write a script" problem. Day 1 uses this format now.

**Flashcards, quiz and points.** Each day page has a flashcard deck (beside the page on wide screens, after the
warm-up on small screens). Flip a card, read what the command is, its useful flags and an example, then press
**Got it** or **Again**. "Again" cards come back in **Review**. **Type mode** asks the user to type the command.
Cards link to the problems that use them, and problems link to their cards. The warm-up is flip cards, and the
**Quick quiz** asks 5 multiple-choice questions from the day's cards. Solved problems, cards and quiz answers give
points (top bar), and a finished day gives 50 points.
When the timer reaches 90 minutes the app says "Time is up" and adds unfinished problems to the Review queue.

**Crash week:** the switch at the top shows only the 35 core (★) problems, 5 per day, 7 days.

## Files

| File | What it is |
|---|---|
| `devops-bash-linux.html` | The finished app (built file, do not edit by hand) |
| `template.html` | The app code: HTML, CSS and JavaScript, with a placeholder for the data |
| `data/dayNN.json` | One file per day: setup, problems, answers, interview questions, recap |
| `data/SCHEMA.md` | The JSON format of a day file |
| `data/STYLE.md` | The plain-English writing rules |
| `data/verify-report.json` | Written by `verify.py`; `build.py` reads it |
| `verify.py` | Runs every solution in a clean sandbox and records the real output |
| `build.py` | Joins `template.html` + `data/*.json` into `devops-bash-linux.html` |

## Rebuild after a change

```bash
python3 verify.py          # all days (about 3 minutes); or: python3 verify.py 5 6
python3 build.py
```

`build.py` refuses to build if a problem marked `"verified": true` has not passed `verify.py`,
or was changed after the last run. `python3 verify.py --check-only` checks only the content rules.

## Add a new problem

1. Open `data/dayNN.json` and copy an existing problem object inside `"problems"`.
2. Give it a new id (`d05p08`), and write `situation`, `task`, 3 `hints`, `solution`, `explanation`,
   1-3 `mistakes`, `interview_say` and `try_yourself`. See `data/SCHEMA.md` and `data/STYLE.md`.
3. Leave `expected_output` empty. `verify.py` fills it.
4. If the problem needs files, add commands to the day's `setup` (one paste, no TAB characters).
5. Optional: add `"checks": [{"run": "command", "expect": "text"}]` to prove that an error message in `mistakes` is real.
6. Set `"optional": true` for an extra problem (not counted in the 90 minutes), `"core": true` for the crash week.
7. Run `python3 verify.py NN` and `python3 build.py`.

Code fields (`setup`, `solution`) can be a string or a list of lines. Lists are easier to read.

## How verify.py works (and what it changes)

For each problem it:

1. makes a new empty temp folder and uses it as `HOME`,
2. runs the day's `setup`, then the `solution`, from `~/bash-practice/dayNN/<workdir>`,
3. runs inside a pseudo-terminal, so `ls` prints columns like a real terminal,
4. checks the exit code (`expect_exit`, default 0) and saves the output into the JSON.

It also runs every day **in order in one sandbox** (like the learner does). If a problem with
"Check my output" gives a different output that way, the run fails. This found several real clashes
between problems while the content was written.

Output is shown exactly as produced, with three small changes so it looks like the learner's terminal:

- the temp HOME path is shown as `/home/wicky`;
- an error from the solution file (`/tmp/.../d05p01.sh: line 3: ...`) is shown as `bash: ...`, like in an interactive shell;
- terminal colour codes are removed.

As root, `verify.py` runs the commands as a normal user called `wicky`, because root ignores file permissions.
Create it first in a test machine or container: `useradd -m -s /bin/bash wicky`.
On a normal user account it runs as that user. It never touches your real `~/bash-practice`.

The sandbox was Ubuntu 24.04 with bash 5.2, GNU coreutils 9.4, mawk, jq 1.7, ShellCheck 0.9, systemd 255.

## Problems that are not auto-verified (6)

These need root, systemd, a second server, or the internet, so their output is labelled
**"Typical output (not auto-verified)"** in the app:

| Id | Problem | Where the typical output comes from |
|---|---|---|
| d03p06 | Users, groups, chown and sudo | A real run as root in the test container (not by verify.py) |
| d16p04 | systemctl and journalctl | Written from the standard systemd output format |
| d16p07 | at: run a job once | Written from the standard `at` output format |
| d18p07 | dig, nslookup, nc and traceroute | Written from the standard output formats (needs internet) |
| d19p07 | SSH tunnel to a private database | Written from the standard output formats (needs servers) |
| d20p07 | update-alternatives | Written from the standard output format (needs two Java versions) |

All of them are Extra (optional) problems except d16p04, which is a timed concept problem with
"read only" steps for WSL without systemd.

## Choices made (the simplest option was used when something was unclear)

1. **Folder:** the app lives in `devops-bash-app/` inside this repository ("or the current folder").
2. **Crash week has 35 core problems (5 per day), not about 42.** Six realistic 12-14 minute problems do not fit
   in 90 minutes, and the rules say never to shrink estimates. All 7 crash days are 81-88 minutes.
3. **Day 28's interview round is 20 minutes** (36 questions). The day is still 88 minutes in total.
4. **Mocks for cloud tools.** `kubectl`, `docker`, `aws`, `terraform`, `nginx` and `systemctl` are small mock
   scripts in `mockbin/` (Day 24 and Day 26). They print or read saved JSON. The app says so in every such problem.
5. **Local test servers.** Network problems use `python3 -m http.server` or a tiny fake API on `127.0.0.1`,
   so curl, ss, lsof and "port already in use" are real.
6. **Fixed times and names** where output would change: `touch -d`, `STAMP=...`, `FAKE_NOW=...`, and a git repo
   with fixed author dates (Day 27), so the learner's output matches the recorded output.
7. **Problems with output that always changes** (PIDs, dates, your own disk sizes) have the "Check my output"
   box turned off and a note. 162 problems have the box.
8. **Ubuntu 22.04 differences** are noted where they matter (for example `stat: cannot stat` vs `cannot statx`,
   curl's `(#0)`, systemd and ShellCheck wording).
9. **The sandbox user's id is 30033**, not 1000 like on WSL; Day 3 says so.
10. **British spelling** (normalise, neighbour) is kept, as used in Sri Lanka.
11. **Progress is saved in `localStorage`**. If the browser blocks it, the app still works and shows a warning;
    use Export/Import to move progress between browsers.
12. **The claude.ai Artifact version** cannot download files or open the print dialog (the viewer blocks them).
    Export shows the JSON to copy instead, and the Cheat sheet says to print from the downloaded file.

## Safety

- Everything happens inside `~/bash-practice/dayNN/`. "Reset this day" deletes only that folder.
- No exercise changes your real `~/.ssh`, `/etc/fstab`, `/etc/hosts`, `sshd_config` or firewall. Practice copies are used.
- The few steps that change your system (Day 3 user management, Day 16 crontab and systemd) have a warning and a clean-up step.
