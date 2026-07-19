# EveryCli Sentinel — Build Week evidence

EveryCli began as a fast semantic retriever for CLI commands. For OpenAI Build
Week, we are extending it into **EveryCli Sentinel**: an intent-to-command
planner for Linux users who need to understand the impact of a command before
they paste it into a terminal.

## What is new

`everycli plan "..."` retrieves commands from the existing local, curated
corpus, then produces a reviewable plan:

- the exact corpus command selected;
- a deterministic risk level (`low`, `medium`, or `high`);
- preflight checks and an explicit confirmation requirement for state-changing
  or destructive commands;
- a hard guarantee that planning never executes a shell command.

When `OPENAI_API_KEY` is set, the optional GPT-5.6 planner ranks and explains
only the retrieved candidates. It is intentionally not allowed to invent or
edit shell commands. The final command and risk classification are validated
locally in EveryCli.

```bash
export OPENAI_API_KEY="..."
everycli plan "remove unused Docker images safely"

# Offline/demo fallback: no network or API key required
everycli plan --local "see which branch I am on"
```

## How Codex was used

Codex was used to inspect the existing daemon/search architecture, identify
corpus-routing and validation gaps, and implement the Sentinel planning layer:

1. designed the corpus-grounded safety boundary and local risk rules;
2. added the optional GPT-5.6 Responses API adapter with strict candidate
   validation;
3. added the user-facing `plan` command and focused safety tests;
4. prepared the validation and demo narrative in this document.

The required Build Week submission field should contain the `/feedback` session
ID from the Codex session where the main implementation was completed. Do not
invent this ID; copy it from Codex at submission time.

## Retrieval quality gate

The repository now contains `eval/confusion_set.yaml`: 64 maintained French
and English requests spanning Git, Docker, Compose, Composer, npm, SSH,
Python and Linux. Run the same hybrid matcher as the product with:

```bash
python tools/evaluate_confusion.py
```

The current local baseline is **62/64 top-1 and 64/64 top-3**. This is an
internal regression set, not an external benchmark or a promise about every
possible CLI question. `--show-top1-misses` makes the remaining ambiguities
visible, and `--fail-under <percent>` can be used in CI once the team agrees
on a threshold.

## Demo script (under 3 minutes)

1. Start with a real Linux task: "remove unused Docker images safely".
2. Run `everycli plan ...` and show the selected command, risk level and
   preflight checks.
3. Point out that the tool never auto-executes the command.
4. Run the same request with `--local` to show the offline safety fallback.
5. Explain the AI boundary: GPT-5.6 can interpret intent and explain a choice;
   EveryCli supplies the command from its curated corpus and enforces risk
   rules locally.

## Submission checklist

- [ ] Run the corpus validator and test suite in a working Python environment.
- [ ] Run `python tools/evaluate_confusion.py` and retain its output as demo evidence.
- [ ] Add the public repository URL to Devpost.
- [ ] Record a public video under three minutes, including a spoken explanation
      of Codex and GPT-5.6 usage.
- [ ] Add the actual `/feedback` session ID to the Devpost submission.
- [ ] Choose **Developer Tools** as the category.
