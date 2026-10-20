# Plain-English style guide

The learner reads English as a second language. Every text in the day files follows these rules.

## Words and sentences

- Short sentences. One idea per sentence. Aim for 15 words or fewer.
- Common words. Write "use", not "utilise". Write "start", not "initiate".
- No slang, no idioms ("piece of cake", "out of the box", "under the hood").
- Explain a new word the first time it appears: "A **symlink** (symbolic link) is a shortcut to another file."
- Same word for the same thing. Do not switch between "folder" and "directory" in one problem. Say "folder (directory)" once, then pick one.

## Person

- Explanations and notes: write "the user", not "you".
  Example: "The user runs `ls -a` to see hidden files."
- Task steps may use the imperative: "Create a folder called `logs`."

## Shape

- Explanations: a few short lines, or a small table.
- Use a comparison table when two things are easy to confuse (`[ ]` vs `[[ ]]`, `kill` vs `kill -9`).
- Hints: hint 1 is a gentle push, hint 2 names the command, hint 3 is almost the answer.
- Mistakes: write the exact error text the user will see, in backticks.
- "How to say it in the interview": 1-2 sentences a person can say out loud.

## Honesty

- Never type output by hand. `verify.py` fills `expected_output` from a real run.
- If something cannot run in the sandbox, set `verified: false` and give `typical_output`. The app labels it "Typical output (not auto-verified)".
- Say when output will be different on the learner's machine (process IDs, dates, sizes, user ids).

## Known weak points (repeat them often)

- `/` (forward slash, Linux paths) vs `\` (backslash, Windows paths and escape character).
- Root directory `/` vs root user (`root`, home folder `/root`).
- Single quotes (no expansion) vs double quotes (`$var` expands).
- `return` (exit code 0-255 only) vs `echo` (real output) in functions.
- `ps aux` letters: a = all users, u = user-oriented format, x = also processes without a terminal.
- "others" permission (everyone else) vs root (root ignores most permissions).
