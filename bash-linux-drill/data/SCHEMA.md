# Day file schema (`data/dayNN.json`)

One file per day: `day01.json` ... `day28.json`.
`build.py` reads every file and embeds it in the HTML.
`verify.py` runs the code and writes the real output back into the file.

## Multi-line code

`setup`, `reset` and `solution` can be:

- one string (use `\n` for new lines), or
- a list of strings, one per line (easier to read and edit by hand).

Both forms are the same to `build.py` and `verify.py`.

## Day object

| Field | Type | Meaning |
|---|---|---|
| `day` | number | 1 to 28 |
| `week` | number | 1 to 4 |
| `title` | string | Short title of the day |
| `goal` | string | One short sentence |
| `minutes` | number | Always 90 (the hard limit) |
| `review_day` | bool | `true` for days 7, 14, 21, 28 (optional) |
| `interview_minutes` | number | Optional. Minutes for the interview round (default 7). Day 28 uses 20 for 36 questions |
| `checklist` | list of strings | Optional. A final checklist with checkboxes (saved in the browser). Used on Day 28 |
| `needs` | list of strings | Extra Ubuntu packages, for example `["tree"]`. The app shows `sudo apt install -y ...` (optional) |
| `setup` | code | One paste. Creates `~/bash-practice/dayNN/` and all sample files. Must end with `cd ~/bash-practice/dayNN` |
| `reset` | code | Deletes only that day's folder: `rm -rf ~/bash-practice/dayNN` |
| `warmup` | list | 3-4 objects `{"q", "a", "from_day"}` |
| `problems` | list | Problem objects (see below) |
| `interview` | list | 5 objects `{"q", "a", "topic"}` (review days may have more) |
| `recap` | list | Objects `{"cmd", "meaning", "example", "topic"}`. These build the Cheat sheet |
| `coverage` | list | Objects `{"item", "problems": ["d01p01", ...]}`. Proves every topic item is covered |

## Problem object

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `dNNpMM`, unique, for example `d01p03` |
| `title` | string | Short title |
| `type` | string | One of `command`, `fix-bug`, `predict`, `explain-error`, `convert`, `incident`, `script`, `concept` |
| `topic` | string | Cheat-sheet topic, for example `Files`, `Text`, `Permissions` |
| `minutes` | number | Real time for a beginner: 10-15 for timed problems |
| `optional` | bool | `true` = Extra problem, not counted in the 90 minutes |
| `core` | bool | `true` = used in the Crash week plan |
| `workdir` | string | Folder (inside the day folder) where the solution runs. Default `.` |
| `situation` | string | 2-3 line real-world story |
| `task` | list of strings | Numbered steps |
| `hints` | list of 3 strings | Gentle, medium, almost the answer |
| `solution` | code | The real-world answer. Runs with `bash` from `workdir` |
| `explanation` | list | Objects `{"part", "meaning"}` |
| `expected_output` | string | **Written by `verify.py` only. Never by hand.** |
| `expect_exit` | number | The exit code `verify.py` expects. Default `0`. Use it for "explain the error" problems |
| `output_check` | bool | `true` = show the "Check my output" box (only for fixed output) |
| `output_note` | string | Optional. For example "Dates and sizes will be different on your machine." |
| `verified` | bool | `false` = cannot run safely in the sandbox (needs root, systemd, real network). Then `typical_output` is used |
| `typical_output` | string | Only when `verified` is `false`. Shown with the label "Typical output (not auto-verified)" |
| `mistakes` | list of strings | 1-3 common mistakes, with the exact error text |
| `interview_say` | string | 1-2 simple sentences |
| `try_yourself` | string | A small variation to try |
| `checks` | list | Optional. Objects `{"run": "command", "expect": "text"}`. `verify.py` runs each command after setup and checks that the output contains the text. This proves the error messages in `mistakes` are real |
| `table` | object | Optional comparison table shown with the answer: `{"head": [...], "rows": [[...], ...]}` |

## Teaching ("step-style") problems

A problem can teach from the beginning instead of showing one block of commands.
It then has `steps` instead of `solution`. The app shows: the lesson, the bug table (fix-bug),
the correct script, then each step with its own real output.

| Field | Type | Meaning |
|---|---|---|
| `outcomes` | list of strings | "You will learn" box, shown above the task |
| `spec` | list of strings | "What the script must do". Required for `fix-bug` and `script` problems |
| `learn` | list | The lesson. Sections `{"title", "text": [...], "art", "table", "code", "code_label", "after"}`. `art` is a text diagram (code) |
| `files` | list | Files the user writes or fixes: `{"name", "say", "content"}`. Shown as "The correct script" |
| `steps` | list | `{"say", "code", "run", "edit", "after", "out"}`. `say` = what and why, `after` = what the output shows |

Step details:

- `run: false` = the step is shown but `verify.py` does not run it (an editor, or output that changes on every machine).
- `edit: "name"` = in this step the user edits the file. `verify.py` writes the file's `content` here.
- `out` is **written by `verify.py` only**. It puts a marker line before each step and splits the real output.
- The day's `expected_output` is all step outputs joined, so "Check my output" still works.

## Flashcards (`cards`, day level)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `dNNcMM`, unique |
| `q` | string | The question on the front |
| `a` | string | The short answer (usually a command) |
| `accept` | list of strings | Optional. Other answers that count as right in "Type mode" |
| `what` / `does` | string | What it is / what it does (back of the card) |
| `flags` | list | Optional. `[["-a", "meaning"], ...]` |
| `example` | code | Optional. One or two example commands |
| `links` | list of ids | Problems of the same day where the user practises it. The problem shows the card, the card links back |
| `topic` | string | Cheat-sheet topic |

A day without `cards` gets simple cards made from its recap rows. The quick quiz uses the cards' answers.

## Rules that `verify.py` checks (the build fails if one is broken)

1. Each problem with `verified: true` runs: fresh sandbox, then `setup`, then `solution`. The exit code must equal `expect_exit`.
2. Timed problems: 4 to 6 per day, each 10-15 minutes.
3. Day time: 8 (warm-up) + timed problems + 7 (interview, or `interview_minutes`) + 5 (recap) must be 90 or less.
4. At least one `fix-bug` problem per day.
5. Problem ids are unique, and every id in `coverage` exists.
6. `verified: false` problems must have `typical_output`.
7. Step-style problems need `learn`, a `say` on every step, and `spec` for `fix-bug` and `script` problems.
8. A day in the teaching style needs at least one timed `script` problem (the user writes a script).
9. Cards: id `dNNcMM`, `q`, `a`, `what`, `topic`; every `links` id exists.
