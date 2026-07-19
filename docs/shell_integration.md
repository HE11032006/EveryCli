# EveryCli shell integration

EveryCli separates the human interface from the shell protocol so a command is
never executed by surprise.

## Options

- `-i` / `--interactive`: choose between several search candidates.
- `-s` / `--shell`: display the result and ask for confirmation on `stderr`.
  After a positive confirmation, `stdout` contains exactly one value: the raw
  selected command followed by a newline. A refusal produces no stdout.

`-s` deliberately cannot be combined with `-i`, `--run`, `--copy`, `--error`,
or `--top` other than `1`. This keeps it safe to consume from a wrapper.

## PowerShell

During local development, load the integration once per terminal:

```powershell
. D:\EveryCli\everycli.ps1
evc "annuler mon dernier commit sans perdre mes changements"
```

`evc` captures only the confirmation result and asks PSReadLine to put it in
the editable command buffer. You can still modify it, or press Enter yourself.
If PSReadLine is not available, the wrapper displays the command for manual
copying. It never executes the command.

For a packaged executable, set `EVERYCLI_BIN` to its full path before sourcing
the wrapper. Without it, the wrapper first looks for `everycli.exe`, then for
the repository's `.venv\Scripts\python.exe`.
