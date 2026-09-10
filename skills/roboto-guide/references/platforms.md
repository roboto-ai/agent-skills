# Platform guide

How the skill's commands and file locations change on macOS, Linux, and Windows. Every command elsewhere in this skill is written for a POSIX shell; this file translates them.

Run `python3 scripts/roboto_docs.py env` first (on Windows, `py -3 scripts\roboto_docs.py env`). It prints the platform, the Python that ran it and whether the SDK can use it, whether `uv` and the `roboto` CLI are on `PATH`, whether credentials are present, and the runner to use, without printing any secret.

The file locations below were read from the SDK source at the release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`; the install steps come from the SDK README.

## Command translation

| Task | macOS and Linux | Windows PowerShell | Windows cmd |
|---|---|---|---|
| Run the docs script | `python3 scripts/roboto_docs.py ...` | `py -3 scripts\roboto_docs.py ...` (`python` if the `py` launcher is missing) | same as PowerShell |
| Check the Python version | `python3 --version` | `py -3 --version` | same |
| Create the fallback environment | `python3 -m venv ~/.cache/roboto-guide/venv` | `py -3 -m venv $env:LOCALAPPDATA\roboto-guide\venv` | `py -3 -m venv %LOCALAPPDATA%\roboto-guide\venv` |
| The fallback environment's interpreter and pip | `<venv>/bin/python`, `<venv>/bin/pip` | `<venv>\Scripts\python.exe`, `<venv>\Scripts\pip.exe` | same |
| Install with an extra | `pip install 'roboto[analytics]'` (zsh needs the quotes; see "macOS notes") | `pip install 'roboto[analytics]'` | `pip install roboto[analytics]` (cmd passes quotes through literally) |
| Run a generated script | `uv run script.py`, or the venv interpreter | same; the `#!` line is inert (see "Windows notes") | same |
| Read the latest release tag | `curl -s <url> \| python3 -c ...` | `curl.exe -s <url> \| py -3 -c ...` (in Windows PowerShell 5.1, `curl` alone is an alias for `Invoke-WebRequest`) | `curl -s <url> \| py -3 -c ...` |
| Set a metadata value with embedded quotes | `--metadata 'serial="1234"'` | set it from a script with `put_metadata` (see "Windows notes") | same advice |

Python and the SDK accept forward slashes in Windows paths, so a script's arguments can keep them. Backslashes matter only where the shell resolves the path itself, as when invoking the venv interpreter; PowerShell accepts either form there, and cmd needs backslashes.

## Where things live

| | macOS | Linux | Windows |
|---|---|---|---|
| Credentials file | `~/.roboto/config.json` | same | `%USERPROFILE%\.roboto\config.json` (the SDK builds the path from the home directory; `ROBOTO_CONFIG_FILE` overrides it everywhere) |
| Roboto's local cache | `roboto cache where` prints the CLI's directory on every platform; a script chooses where topic data lands with the `cache_dir=` argument (see the cookbook, "Topics and time-series data") | same | same |
| Fallback environment the skill builds | `~/.cache/roboto-guide/venv` | same | `%LOCALAPPDATA%\roboto-guide\venv` |
| Claude Code skills directory | `~/.claude/skills` | same | `%USERPROFILE%\.claude\skills` |

## Python, uv, and the CLI per platform

The SDK needs Python 3.11 or newer; the docs script runs on 3.9 or newer. "The latest release" below is https://github.com/roboto-ai/roboto-python-sdk/releases/latest.

| | macOS | Linux | Windows |
|---|---|---|---|
| Python the system ships | 3.9 with the Xcode command line tools, too old for the SDK | Ubuntu 22.04 ships 3.10 (too old), Debian 12 ships 3.11, Ubuntu 24.04 ships 3.12; check `python3 --version` | none by default; `python` and `python3` typed at a prompt open the Microsoft Store until an interpreter is installed |
| A new enough Python | `brew install python@3.12`, or let `uv` fetch one | the distribution's package for 3.11+, or `uv` | the python.org installer or `winget install Python.Python.3.12` (both add the `py` launcher), or `uv` |
| `uv` | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| `roboto` CLI | `brew install roboto-ai/tap/roboto`, or the `roboto-macos-aarch64` / `roboto-macos-x86_64` binary from the latest release, made executable and placed on `PATH` | the `.deb` from the latest release installed with `apt`, or the `roboto-linux-<arch>` binary made executable and placed on `PATH` | `roboto-windows-x86_64.exe` from the latest release, placed in a folder on `PATH` |
| Upgrade the CLI | `brew upgrade roboto`, or replace the binary | install the new `.deb`, or replace the binary | replace the `.exe` |

On macOS, prefer the Homebrew install when a downloaded binary refuses to run; Homebrew handles the executable bit and quarantine attributes.

## Windows notes

- Console encoding: the docs script's output is safe to pipe under any code page. Other Python scripts that print SDK docstrings can still raise `UnicodeEncodeError` under a legacy code page; set `PYTHONUTF8=1` for the session if that happens.
- No shebang support: the `#!/usr/bin/env -S uv run --script` line in a generated script is inert. Run the script as `uv run script.py`, which reads the inline metadata block without it, or as `<venv>\Scripts\python.exe script.py`.
- `py -3` runs the newest installed Python 3; `py -3.12` pins one. `python3` as a command exists only when Python was installed from the Microsoft Store.
- PowerShell and cmd quote differently: single quotes are literal in PowerShell and ordinary characters in cmd, and PowerShell's handling of embedded double quotes in arguments to native commands changed in 7.3. A value that must contain double quotes belongs in a script, not on the command line.

## macOS notes

- zsh, the default shell, expands `[...]` as a glob, so quote package specs with extras and RoboQL queries that contain brackets (`'msgpaths[cpuload.load].mean > 0.8'`).
