# EveryCli shell integration

EveryCli separates the human interface from the shell protocol so a command is
never executed by surprise.

## Options

- `-i` / `--interactive`: choose between several search candidates (real
  arrow-key selection via `inquire`, not a typed number).
- `-s` / `--shell`: machine-readable protocol for wrapper scripts. All
  diagnostics (namespace/id, command, explanation, score) go to `stderr`.
  `stdout` carries exactly one value: the raw resolved command, with no
  trailing newline. There is no confirmation prompt in `-s` mode itself —
  the wrapper (see below) is what decides whether to ask before running it.

`-s` deliberately cannot be combined with `-i`, `--run`, `--copy`, `--error`,
or `--top` other than `1`. This keeps it safe to consume from a wrapper.

## PowerShell

During local development, load the integration once per terminal:

```powershell
. D:\EveryCli\everycli.ps1
evc "annuler mon dernier commit sans perdre mes changements"
```

`evc` captures only the resolved command from `-s` mode and asks PSReadLine to
put it in the editable command buffer. You can still modify it, or press
Enter yourself. If PSReadLine is not available, the wrapper displays the
command for manual copying. It never executes the command itself.

For a packaged executable, set `EVERYCLI_BIN` to its full path before sourcing
the wrapper. Without it, the wrapper first looks for `everycli.exe` (installed
via `install.ps1`, on the `PATH`), then falls back to the repository's
`.venv\Scripts\python.exe` (legacy Python flow, see
[CHANGELOG.md](../CHANGELOG.md)).
