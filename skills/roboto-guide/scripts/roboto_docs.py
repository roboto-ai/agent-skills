#!/usr/bin/env python3
"""Resolve names to pages on docs.roboto.ai and print pages as text.

docs.roboto.ai is built with Sphinx, which publishes two artifacts this script
relies on:

* ``objects.inv``, a zlib-compressed index of every documented page, Python
  symbol, and CLI option, each with the URL that documents it.
* ``_sources/<page>.rst.txt``, the reStructuredText source of every page.

Subcommands:

  search <term> [<term> ...]   List inventory entries whose name or title
                               contains every term (case-insensitive), with
                               the URL of each.
  fetch <target>               Print one page, or one symbol's section of a
                               page, as text. ``target`` is a page path
                               (``learn/sdk``), a URL under docs.roboto.ai, or
                               a symbol name from ``search``
                               (``roboto.Dataset.from_id``).
  versions                     Print the SDK release the skill's reference
                               files were last checked against (from the
                               ``metadata`` block of SKILL.md), the latest
                               release on PyPI and GitHub, and the installed
                               CLI version, then say whether the references
                               are behind.
  env                          Print what this machine offers: platform and
                               shell, the Python running the script and
                               whether the SDK can use it, uv and the roboto
                               CLI with versions, whether credentials are
                               present (never their values), and the path
                               the no-uv fallback environment would use.
  restapi [<term> ...]         List REST API endpoints whose path, tag,
                               operation ID, or summary contains every term.
                               With --path (and optionally --method), print
                               one endpoint's parameters, request body, and
                               response schema. Reads the OpenAPI document
                               embedded in https://docs.roboto.ai/restapi.html
                               and caches it for 24 hours.

Standard library only. Runs on Python 3.9 or newer.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib
from html.parser import HTMLParser

BASE_URL = "https://docs.roboto.ai/"
USER_AGENT = "roboto-guide-skill (+https://github.com/roboto-ai/agent-skills)"
INVENTORY_MAX_AGE_SECONDS = 24 * 60 * 60
PYPI_JSON_URL = "https://pypi.org/pypi/roboto/json"
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest"
# A Redoc page. Its OpenAPI 3.1 document is embedded as the JavaScript
# variable ``__redoc_state``, under ``spec.data``.
RESTAPI_URL = "https://docs.roboto.ai/restapi.html"
# SKILL.md sits one directory above scripts/. Its frontmatter ``metadata``
# block is the one place that records which SDK release and date the files
# under references/ were last checked against.
SKILL_FILE = pathlib.Path(__file__).resolve().parent.parent / "SKILL.md"

# Each ``--role`` value selects a set of Sphinx ``domain:role`` strings. The
# comment on each line says what those rows are in this site's inventory.
ROLE_ALIASES = {
    "doc": {"std:doc"},                                    # one row per page; title is the page title
    "label": {"std:label"},                                # reST section targets such as topics-section on learn/concepts
    "cli": {"std:cmdoption"},                              # one row per option or positional argument of each roboto subcommand, named roboto-<group>-<command>.<option>; no rows for subcommands themselves
    "module": {"py:module"},                               # Python modules
    "class": {"py:class", "py:exception"},                 # classes and exception classes
    "function": {"py:function", "py:method", "py:property"},  # functions, methods, and properties
    "attribute": {"py:attribute", "py:data", "py:type"},   # class attributes, module-level data, and type aliases
}

# One objects.inv v2 line: ``{name} {domain}:{role} {priority} {uri} {dispname}``.
# ``name`` may contain spaces (pydantic type expressions do on this site), so it
# is matched lazily up to the first ``domain:role`` token.
INVENTORY_LINE = re.compile(r"^(?P<name>.+?)\s+(?P<role>\S+:\S+)\s+(?P<priority>-?\d+)\s+(?P<uri>\S+)\s+(?P<dispname>.*)$")

# In the PyData Sphinx Theme, ``<main>`` holds the article and also the primary
# sidebar (class ``bd-sidebar-primary bd-sidebar``) and the secondary sidebar
# (class ``bd-sidebar-secondary bd-toc``) whose "On this page" heading is not
# article text. ``headerlink`` is the ``<a>`` Sphinx appends to every heading
# and signature, whose text is a lone ``#``. Elements whose class contains any
# of these are skipped.
SKIP_CLASS_FRAGMENTS = ("bd-sidebar", "bd-toc", "headerlink")

# HTML void elements never get an end tag, so they must not change the nesting
# depth the parser tracks.
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def cache_dir() -> pathlib.Path:
    """ROBOTO_DOCS_CACHE_DIR if set, else ``$XDG_CACHE_HOME/roboto-docs``.

    Per the XDG Base Directory Specification, XDG_CACHE_HOME defaults to
    ``$HOME/.cache`` when unset or empty, and a relative value is invalid and
    ignored.
    """
    override = os.environ.get("ROBOTO_DOCS_CACHE_DIR")
    if override:
        return pathlib.Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    root = pathlib.Path(xdg) if xdg and os.path.isabs(xdg) else pathlib.Path.home() / ".cache"
    return root / "roboto-docs"


def http_get(url: str, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_inventory(refresh: bool = False) -> list[tuple[str, str, str, str]]:
    """Return (name, role, uri, dispname) rows from objects.inv.

    ``dispname`` is Sphinx's display name for the entry. Sphinx writes ``-``
    when it equals ``name``, and this function reads ``-`` back as ``name``.
    On this site it differs from ``name`` only for ``std:doc`` rows (the page
    title) and ``std:label`` rows (the section title, or ``-`` for a label
    with no title).

    The downloaded file is kept at ``cache_dir()/objects.inv`` and downloaded
    again only when it is absent, older than INVENTORY_MAX_AGE_SECONDS, or
    ``refresh`` is true.
    """
    path = cache_dir() / "objects.inv"
    needs_download = True
    if path.is_file() and not refresh:
        needs_download = (time.time() - path.stat().st_mtime) > INVENTORY_MAX_AGE_SECONDS
    if needs_download:
        try:
            raw = http_get(BASE_URL + "objects.inv")
        except (urllib.error.URLError, OSError) as exc:
            if path.is_file():
                print(f"warning: could not download objects.inv ({exc}); using the copy at {path}", file=sys.stderr)
                raw = path.read_bytes()
            else:
                raise SystemExit(f"error: could not download {BASE_URL}objects.inv: {exc}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    else:
        raw = path.read_bytes()

    # The v2 header is four ``#`` lines; the last one names zlib, and the
    # compressed body starts on the line after it.
    header_end = raw.index(b"\n", raw.index(b"zlib")) + 1
    body = zlib.decompress(raw[header_end:]).decode("utf-8", errors="replace")
    rows = []
    for line in body.splitlines():
        match = INVENTORY_LINE.match(line)
        if not match:
            continue
        name, role, uri, dispname = match["name"], match["role"], match["uri"], match["dispname"]
        if dispname == "-":
            dispname = name
        # When the anchor ends with the entry name, the v2 format replaces that
        # suffix with ``$``: ``#$`` for most symbols, ``#module-$`` for
        # ``py:module`` rows. Sphinx's reader restores the name after any
        # trailing ``$``.
        if uri.endswith("$"):
            uri = uri[:-1] + name
        rows.append((name, role, uri, dispname))
    return rows


def resolve_roles(requested: list[str] | None) -> set[str] | None:
    if not requested:
        return None
    roles: set[str] = set()
    for item in requested:
        roles |= ROLE_ALIASES[item]
    return roles


def cmd_search(args: argparse.Namespace) -> int:
    rows = load_inventory(refresh=args.refresh)
    terms = [t.lower() for t in args.terms]
    roles = resolve_roles(args.role)

    scored = []
    for name, role, uri, dispname in rows:
        if roles and role not in roles:
            continue
        haystack = f"{name} {dispname}".lower()
        if not all(t in haystack for t in terms):
            continue
        # Every term filters; only the first term ranks. Rank 0: the whole name
        # or its last dotted segment equals the first term. Rank 1: the name ends
        # with the first term. Rank 2: any other substring match. Ties sort by
        # name length, then role, then name.
        lowered = name.lower()
        if lowered == terms[0] or lowered.rsplit(".", 1)[-1] == terms[0]:
            rank = 0
        elif lowered.endswith(terms[0]):
            rank = 1
        else:
            rank = 2
        scored.append((rank, len(name), role, name, uri, dispname))

    scored.sort()
    if not scored:
        print("no matches")
        return 1
    shown = scored[: args.limit]
    for _, _, role, name, uri, dispname in shown:
        title = f"  ({dispname})" if dispname != name else ""
        print(f"{role:14} {name}{title}\n{'':14} {BASE_URL}{uri}")
    if len(scored) > len(shown):
        print(f"... {len(scored) - len(shown)} more; narrow the terms or raise --limit")
    return 0


class _ArticleText(HTMLParser):
    """Collect the text of a docs.roboto.ai page with light Markdown markup.

    Extraction starts at the first ``<main>``, ``<article>``, or element with
    class ``bd-article`` (the PyData Sphinx Theme's article container) and
    stops when that element closes. Inside it, ``script``, ``style``, ``nav``,
    ``header``, ``footer``, ``aside``, and any element whose class contains a
    SKIP_CLASS_FRAGMENTS entry are dropped. Headings become ``#`` lines,
    ``<pre>`` blocks become fenced code, table cells are separated by `` | ``,
    and other block elements start a new line. Runs of whitespace outside
    ``<pre>`` collapse to one space.

    ``anchors`` records, for every element with an ``id``, the index into
    ``parts`` where its text begins and the element's nesting depth, so a caller
    can cut out one section. Sphinx gives a section two ids when it has both a
    title and an explicit label (``.. _topics-section:``) or a ``py:module``
    target: one on the ``<section>`` and one on an empty ``<span>`` that opens
    inside it before any text. Such a span is recorded as an alias of the
    section (same start and depth) so that a cut at either id covers the whole
    section, nested subsections included.
    """

    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside"}
    BLOCK_TAGS = {"p", "div", "li", "dt", "dd", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "section", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_stack: list[int] = []  # depths at which a skipped element was opened
        self._open_tags: list[str] = []  # names of the open non-void elements, outermost first
        self._in_pre = False
        self._in_article = False
        self._article_depth = 0
        self._depth = 0
        self._section_start: tuple[int, int] | None = None  # (parts index, depth) of the innermost open section
        self.anchors: dict[str, tuple[int, int]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_TAGS:
            if tag in ("br", "hr") and self._in_article and not self._skip_stack:
                self.parts.append("\n")
            return
        parent = self._open_tags[-1] if self._open_tags else ""
        self._open_tags.append(tag)
        self._depth += 1
        attr = dict(attrs)
        classes = attr.get("class") or ""
        if tag in self.SKIP_TAGS or any(fragment in classes for fragment in SKIP_CLASS_FRAGMENTS):
            self._skip_stack.append(self._depth)
            return
        if not self._in_article and (tag == "main" or tag == "article" or "bd-article" in classes):
            self._in_article = True
            self._article_depth = self._depth
        if self._skip_stack or not self._in_article:
            return
        position = (len(self.parts), self._depth)
        if (
            tag == "span"
            and parent == "section"
            and self._section_start is not None
            and all(not part.strip() for part in self.parts[self._section_start[0]:])
        ):
            position = self._section_start
        element_id = attr.get("id")
        if element_id:
            self.anchors[element_id] = position
        if tag == "section":
            self._section_start = (len(self.parts), self._depth)
        if tag == "pre":
            self._in_pre = True
            self.parts.append("\n```\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag in ("td", "th"):
            self.parts.append(" | ")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if self._open_tags:
            self._open_tags.pop()
        if self._skip_stack and self._skip_stack[-1] == self._depth:
            self._skip_stack.pop()
        elif self._in_article and not self._skip_stack:
            if tag == "pre":
                self._in_pre = False
                self.parts.append("\n```\n")
            elif tag in self.BLOCK_TAGS:
                self.parts.append("\n")
            if self._depth == self._article_depth:
                self._in_article = False
        self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_stack or not self._in_article:
            return
        if self._in_pre:
            self.parts.append(data)
        else:
            self.parts.append(re.sub(r"\s+", " ", data))

    def text(self, start: int = 0, end: int | None = None) -> str:
        joined = "".join(self.parts[start:end])
        joined = re.sub(r"[ \t]+\n", "\n", joined)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()

    def section(self, anchor: str) -> str | None:
        """Text from the element with id ``anchor`` up to the next element with
        an id at the same or a shallower depth. For a symbol that is the next
        ``<dt id>`` signature; for a section it is the next sibling section.
        None when the id is not on the page."""
        if anchor not in self.anchors:
            return None
        start, depth = self.anchors[anchor]
        end = None
        for other_start, other_depth in self.anchors.values():
            if other_start > start and other_depth <= depth and (end is None or other_start < end):
                end = other_start
        return self.text(start, end)


def html_to_text(page: bytes, anchor: str | None) -> str:
    parser = _ArticleText()
    parser.feed(page.decode("utf-8", errors="replace"))
    if not parser.parts:
        # No <main>, <article>, or bd-article element was found, so this is not
        # a page in the site's theme. Drop script and style bodies, strip every
        # other tag, and return the remaining text nodes.
        stripped = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page.decode("utf-8", errors="replace"))
        stripped = re.sub(r"<[^>]+>", " ", stripped)
        return re.sub(r"\s+", " ", html.unescape(stripped)).strip()
    if anchor:
        section = parser.section(anchor)
        if section is None:
            return f"(no element with id '{anchor}' on this page; printing the whole page)\n\n" + parser.text()
        return section
    return parser.text()


def resolve_target(target: str, refresh: bool) -> tuple[str, str | None]:
    """Map a fetch target to (page path without extension, anchor or None)."""
    anchor = None
    if target.startswith("http://") or target.startswith("https://"):
        if not target.startswith(BASE_URL):
            raise SystemExit(f"error: only URLs under {BASE_URL} are supported")
        target = target[len(BASE_URL):]
    if "#" in target:
        target, anchor = target.split("#", 1)
    target = target.strip("/")
    if target.endswith(".html"):
        target = target[: -len(".html")]
    if target.endswith(".md"):
        target = target[: -len(".md")]
    if target == "":
        target = "index"

    # A dotted name with no slash is read as a Python symbol or CLI option name
    # from the inventory rather than as a page path.
    if "." in target and "/" not in target:
        rows = load_inventory(refresh=refresh)
        exact = [r for r in rows if r[0] == target and r[1] != "std:doc"]
        if not exact:
            raise SystemExit(f"error: no inventory entry named '{target}'; try `search {target}`")
        uri = exact[0][2]
        page, _, symbol_anchor = uri.partition("#")
        return page[: -len(".html")] if page.endswith(".html") else page, symbol_anchor or anchor
    return target, anchor


def rst_source_has_content(text: str) -> bool:
    """True when the page's reST source carries prose or directive bodies.

    The test is whether at least 200 characters remain after dropping directive
    lines (``.. x::``), directive options and field lines (``:x:``), and blank
    lines. Pages that fail it are fetched as HTML instead. Measured on
    2026-09-09 over the site's 313 pages, 22 failed: the CLI reference, whose source is a title
    and one ``.. autoprogram::`` directive so its content exists only in the
    rendered HTML; the four table-of-contents pages (``index``,
    ``learn/index``, ``reference/index``, ``roboql/index``); ``reference/
    rest-api``, which is one link to ``/restapi.html``; and 16 small SDK
    module pages whose docstrings total under 200 characters. The other 241
    autoapi-generated SDK pages carry their signatures and docstrings in the
    source and pass.
    """
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(".. ") or stripped.startswith(":"):
            continue
        kept.append(stripped)
    return len(" ".join(kept)) >= 200


def cmd_fetch(args: argparse.Namespace) -> int:
    page, anchor = resolve_target(args.target, refresh=args.refresh)
    attempts: list[tuple[str, str]] = []
    if not anchor:
        # ``<page>.md``: a Markdown copy of the page, used whenever the site
        # publishes one. The attempt costs one request per whole-page fetch.
        # docs.roboto.ai answered 403 for every such path on 2026-09-09.
        attempts.append(("markdown", f"{BASE_URL}{page}.md"))
        attempts.append(("rst", f"{BASE_URL}_sources/{page}.rst.txt"))
    attempts.append(("html", f"{BASE_URL}{page}.html"))

    for kind, url in attempts:
        try:
            body = http_get(url)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                continue
            raise SystemExit(f"error: {url} returned HTTP {exc.code}")
        except (urllib.error.URLError, OSError) as exc:
            raise SystemExit(f"error: could not fetch {url}: {exc}")

        if kind == "rst":
            text = body.decode("utf-8", errors="replace")
            if not rst_source_has_content(text):
                continue
        elif kind == "markdown":
            text = body.decode("utf-8", errors="replace")
            if text.lstrip().startswith("<"):
                continue  # The body is HTML or XML, not Markdown.
        else:
            text = html_to_text(body, anchor)

        print(f"# source: {url}\n")
        if args.max_chars and len(text) > args.max_chars:
            print(text[: args.max_chars])
            print(f"\n... truncated at {args.max_chars} characters; raise --max-chars to see more")
        else:
            print(text)
        return 0

    tried = ", ".join(url for _, url in attempts)
    raise SystemExit(f"error: every candidate URL returned 403 or 404, or had no page content: {tried}")


def verified_stamp() -> dict[str, str]:
    """Return the ``verified-*`` entries from SKILL.md's frontmatter ``metadata``.

    Expected keys are ``verified-sdk`` (an SDK release such as ``0.55.0``) and
    ``verified-on`` (an ISO date). Missing file or block yields an empty dict.
    """
    try:
        text = SKILL_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    frontmatter = re.match(r"---\n(.*?)\n---", text, re.S)
    if not frontmatter:
        return {}
    stamp: dict[str, str] = {}
    for match in re.finditer(r"^\s+(verified-[a-z]+):\s*\"?([^\"\n]+?)\"?\s*$", frontmatter.group(1), re.M):
        stamp[match.group(1)] = match.group(2)
    return stamp


def version_key(version: str) -> tuple[int, ...]:
    """Leading numeric components of a version string, for ordering.

    ``v0.55.0`` and ``0.55.0`` compare equal; a suffix such as ``rc1`` and
    everything after it is ignored.
    """
    parts: list[int] = []
    for piece in re.split(r"[.\-+]", version.lstrip("v")):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts)


def tool_version(name: str) -> tuple[str, str] | None:
    """Return (path, first line of ``<name> --version``) or None when not on PATH."""
    path = shutil.which(name)
    if not path:
        return None
    try:
        proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30)
        line = (proc.stdout or proc.stderr).strip().splitlines()
        return path, line[0] if line else "(no version output)"
    except (OSError, subprocess.SubprocessError) as exc:
        return path, f"(failed to run: {exc})"


def fallback_venv() -> pathlib.Path:
    """Where the no-uv fallback environment lives (see sdk-cookbook.md, "Without uv")."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return pathlib.Path(os.environ["LOCALAPPDATA"]) / "roboto-guide" / "venv"
    return pathlib.Path.home() / ".cache" / "roboto-guide" / "venv"


def cmd_env(args: argparse.Namespace) -> int:
    windows = os.name == "nt"
    print(f"platform:       {platform.system()} {platform.release()} {platform.machine()}")
    if windows:
        print("shell:          Windows; PowerShell and cmd quote differently, see references/platforms.md")
    else:
        print(f"shell:          {os.environ.get('SHELL', 'unknown')}")

    major, minor = sys.version_info[:2]
    sdk_ok = (major, minor) >= (3, 11)
    print(f"python:         {platform.python_version()} at {sys.executable}")
    print("                " + ("new enough for the roboto SDK (3.11+)" if sdk_ok else "too old for the roboto SDK, which needs 3.11+; use uv or a newer interpreter for scripts"))
    if windows:
        launcher = "py -3" if shutil.which("py") else "python"
        print(f"launcher:       use `{launcher}` where the skill says `python3`")
    elif not shutil.which("python3"):
        print("launcher:       `python3` is not on PATH; use the interpreter above")

    uv = tool_version("uv")
    print(f"uv:             {uv[1]} at {uv[0]}" if uv else "uv:             not found; install it (references/platforms.md) or build the fallback environment below")
    cli = tool_version("roboto")
    print(f"roboto CLI:     {cli[1]} at {cli[0]}" if cli else "roboto CLI:     not found on PATH; references/getting-started.md step 3 installs it")

    endpoint = os.environ.get("ROBOTO_SERVICE_ENDPOINT")
    if endpoint:
        print(f"endpoint:       {endpoint} (from ROBOTO_SERVICE_ENDPOINT)")
    else:
        print("endpoint:       not set in the environment; the config profile decides. If org names or data look unfamiliar,")
        print("                print RobotoClient.from_env().endpoint from a script to confirm which deployment answers")
    config_path = pathlib.Path(os.environ.get("ROBOTO_CONFIG_FILE") or (pathlib.Path.home() / ".roboto" / "config.json"))
    found: list[str] = []
    if os.environ.get("ROBOTO_API_KEY") or os.environ.get("ROBOTO_BEARER_TOKEN"):
        found.append("ROBOTO_API_KEY is set (checked first by the SDK)")
    if config_path.exists():
        found.append(f"config file present at {config_path}")
    print("credentials:    " + ("; ".join(found) if found else f"none: no ROBOTO_API_KEY and no file at {config_path}; see references/getting-started.md step 2"))
    for var in ("ROBOTO_ORG_ID", "ROBOTO_PROFILE", "ROBOTO_SERVICE_ENDPOINT", "ROBOTO_CACHE_DIR"):
        if os.environ.get(var):
            print(f"{var + ':':<16}{os.environ[var]}")

    venv = fallback_venv()
    interpreter = venv / ("Scripts/python.exe" if windows else "bin/python")
    state = "exists" if interpreter.exists() else "absent"
    print(f"fallback venv:  {venv} ({state}); interpreter {interpreter}")
    print(f"docs cache:     {cache_dir()}")

    if uv:
        print("runner:         uv run (preferred)")
    elif interpreter.exists():
        print(f"runner:         {interpreter} (no uv; refresh it with pip install --upgrade 'roboto[analytics]')")
    elif sdk_ok:
        print("runner:         none yet; build the fallback environment (references/sdk-cookbook.md, \"Without uv\") or install uv")
    else:
        print("runner:         none; this Python cannot host the SDK, so install uv or a Python 3.11+ first (references/platforms.md)")
    return 0


def cmd_versions(args: argparse.Namespace) -> int:
    stamp = verified_stamp()
    verified = stamp.get("verified-sdk")
    print(f"references verified against: roboto {verified or 'unknown'} on {stamp.get('verified-on', 'an unrecorded date')}")

    pypi_latest: str | None = None
    newer: list[str] = []
    try:
        data = json.loads(http_get(PYPI_JSON_URL))
        pypi_latest = data["info"]["version"]
        files = data["releases"].get(pypi_latest) or [{}]
        uploaded = str(files[0].get("upload_time", ""))[:10]
        if verified:
            newer = sorted(
                (v for v in data["releases"] if version_key(v) > version_key(verified)),
                key=version_key,
            )
        print(f"PyPI latest:                 roboto {pypi_latest}" + (f" (uploaded {uploaded})" if uploaded else ""))
    except Exception as exc:  # network, JSON shape, or key errors all read the same to the caller
        print(f"PyPI latest:                 unavailable ({exc})")

    try:
        data = json.loads(http_get(GITHUB_LATEST_RELEASE_URL))
        published = str(data.get("published_at", ""))[:10]
        print(f"GitHub latest release:       {data.get('tag_name')}" + (f" (published {published})" if published else ""))
    except Exception as exc:
        print(f"GitHub latest release:       unavailable ({exc})")

    roboto_bin = shutil.which("roboto")
    if roboto_bin:
        try:
            # The CLI writes its own upgrade notice to stderr; only stdout is the version.
            result = subprocess.run([roboto_bin, "--version"], capture_output=True, text=True, timeout=30)
            print(f"installed CLI:               {result.stdout.strip() or 'no output'}")
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"installed CLI:               {roboto_bin} failed to run ({exc})")
    else:
        print("installed CLI:               not on PATH")

    if verified and pypi_latest:
        if newer:
            print(
                f"verdict: {len(newer)} release(s) newer than the verified one: {', '.join(newer)}. "
                "Re-check any signature or flag taken from references/ against source 1 in SKILL.md before using it."
            )
        else:
            print("verdict: references were verified against the latest release.")
    return 0


def load_openapi(refresh: bool = False) -> dict:
    """Return the OpenAPI document embedded in the REST API reference page.

    The page is about 9 MB, so the extracted document (about 2 MB) is cached
    under ``cache_dir()`` for the same 24 hours as the inventory.
    """
    cached = cache_dir() / "openapi.json"
    if not refresh and cached.exists() and time.time() - cached.stat().st_mtime < INVENTORY_MAX_AGE_SECONDS:
        return json.loads(cached.read_text(encoding="utf-8"))
    try:
        page = http_get(RESTAPI_URL, timeout=120.0).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))
        raise SystemExit(f"error: could not fetch {RESTAPI_URL}: {exc}")
    marker = page.find("__redoc_state")
    start = page.find("{", marker)
    if marker < 0 or start < 0:
        raise SystemExit(f"error: {RESTAPI_URL} no longer embeds __redoc_state; open it in a browser instead")
    state, _ = json.JSONDecoder().raw_decode(page[start:])
    spec = state.get("spec", {})
    document = spec.get("data") if isinstance(spec.get("data"), dict) else spec
    if not isinstance(document, dict) or "paths" not in document:
        raise SystemExit(f"error: could not find an OpenAPI document in {RESTAPI_URL}")
    cache_dir().mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(document), encoding="utf-8")
    return document


HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def schema_summary(schema: object, components: dict, depth: int = 0) -> str:
    """Render a JSON Schema fragment as one indented block of ``name: type`` lines.

    ``$ref`` entries are followed into ``components/schemas``, at most three
    levels deep, so a request body prints its fields without a second lookup.
    """
    pad = "  " * depth
    if not isinstance(schema, dict):
        return f"{pad}{schema!r}"
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        target = components.get(name)
        if depth >= 3 or target is None:
            return f"{pad}{name}"
        return f"{pad}{name}:\n" + schema_summary(target, components, depth + 1)
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            parts = [schema_summary(s, components, depth) for s in schema[key]]
            return f"\n{pad}| ".join(p.lstrip() if i else p for i, p in enumerate(parts))
    kind = schema.get("type", "")
    if "enum" in schema:
        return f"{pad}one of {schema['enum']}"
    if kind == "array":
        return f"{pad}array of:\n" + schema_summary(schema.get("items", {}), components, depth + 1)
    if kind == "object" or "properties" in schema:
        required = set(schema.get("required", []))
        lines = []
        title = schema.get("title")
        if title and depth == 0:
            lines.append(f"{pad}{title}")
        for name, prop in schema.get("properties", {}).items():
            flag = " (required)" if name in required else ""
            desc = prop.get("description", "") if isinstance(prop, dict) else ""
            desc = " ".join(desc.split())
            desc = f"  # {desc[:140]}" if desc else ""
            rendered = schema_summary(prop, components, depth + 1).strip()
            if "\n" in rendered:
                lines.append(f"{pad}  {name}{flag}:{desc}\n" + schema_summary(prop, components, depth + 2))
            else:
                lines.append(f"{pad}  {name}{flag}: {rendered}{desc}")
        if not lines:
            lines.append(f"{pad}object" + (" (any keys)" if schema.get("additionalProperties") else ""))
        return "\n".join(lines)
    text = kind or "any"
    if "format" in schema:
        text += f" ({schema['format']})"
    if "default" in schema:
        text += f" = {schema['default']!r}"
    return f"{pad}{text}"


def cmd_restapi(args: argparse.Namespace) -> int:
    document = load_openapi(refresh=args.refresh)
    paths = document["paths"]
    components = document.get("components", {}).get("schemas", {})

    if args.path:
        entry = paths.get(args.path)
        if entry is None:
            raise SystemExit(f"error: no endpoint at {args.path}; run `restapi <term>` to list paths")
        methods = [m for m in HTTP_METHODS if m in entry]
        if args.method:
            wanted = args.method.lower()
            if wanted not in entry:
                raise SystemExit(f"error: {args.path} has no {wanted.upper()}; it has {', '.join(m.upper() for m in methods)}")
            methods = [wanted]
        out: list[str] = [f"# source: {RESTAPI_URL}"]
        for method in methods:
            op = entry[method]
            out.append(f"\n## {method.upper()} {args.path}")
            if op.get("operationId"):
                out.append(f"operationId: {op['operationId']}    tags: {', '.join(op.get('tags', []))}")
            if op.get("summary"):
                out.append(op["summary"])
            if op.get("description"):
                out.append(op["description"].strip())
            params = op.get("parameters", [])
            if params:
                out.append("\nParameters:")
                for prm in params:
                    flag = " (required)" if prm.get("required") else ""
                    rendered = schema_summary(prm.get("schema", {}), components).strip()
                    desc = " ".join(prm.get("description", "").split())
                    out.append(f"  {prm['name']} in {prm.get('in')}{flag}: {rendered}" + (f"  # {desc[:140]}" if desc else ""))
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body is not None:
                out.append("\nRequest body (application/json):")
                out.append(schema_summary(body, components, 1))
            ok = op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema")
            if ok is not None:
                out.append("\nResponse 200 (application/json):")
                out.append(schema_summary(ok, components, 1))
            else:
                codes = ", ".join(sorted(op.get("responses", {})))
                out.append(f"\nResponses: {codes}")
        text = "\n".join(out)
    else:
        terms = [t.lower() for t in args.terms]
        rows: list[str] = []
        for path in sorted(paths):
            entry = paths[path]
            methods = [m for m in HTTP_METHODS if m in entry]
            haystack = " ".join(
                [path]
                + [entry[m].get("operationId", "") for m in methods]
                + [entry[m].get("summary", "") for m in methods]
                + [" ".join(entry[m].get("tags", [])) for m in methods]
            ).lower()
            if all(t in haystack for t in terms):
                op_ids = ", ".join(entry[m].get("operationId", m) for m in methods)
                rows.append(f"{', '.join(m.upper() for m in methods):<22} {path:<58} {op_ids}")
        if not rows:
            raise SystemExit(f"no endpoint matches {' '.join(args.terms)!r}; tags are: {', '.join(sorted({t['name'] for t in document.get('tags', [])}))}")
        header = f"# source: {RESTAPI_URL}\n# {len(rows)} of {len(paths)} paths; use --path <path> for parameters and schemas\n"
        text = header + "\n".join(rows)

    if args.max_chars and len(text) > args.max_chars:
        print(text[: args.max_chars])
        print(f"\n... truncated at {args.max_chars} characters; raise --max-chars to see more")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Agents read this script through a pipe. On Windows a pipe inherits the
    # console code page (cp437, cp1252), and docs pages contain characters
    # outside it, so print UTF-8 and substitute anything unencodable.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    refresh_help = "download objects.inv again even if the cached copy is less than 24 hours old"
    parser.add_argument("--refresh", action="store_true", help=refresh_help)
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="list inventory entries whose name or title contains every term")
    # Accepted after the subcommand as well. SUPPRESS keeps the subparser from
    # overwriting the value the top-level flag set.
    p_search.add_argument("--refresh", action="store_true", default=argparse.SUPPRESS, help=refresh_help)
    p_search.add_argument("terms", nargs="+", help="every term must appear in the entry's name or title")
    p_search.add_argument(
        "--role",
        action="append",
        choices=sorted(ROLE_ALIASES),
        help=(
            "keep only entries of this kind; repeatable. doc: pages. label: reST section targets. "
            "cli: options of roboto subcommands. module: Python modules. class: classes and exceptions. "
            "function: functions, methods, and properties. attribute: attributes, module data, and type aliases"
        ),
    )
    p_search.add_argument("--limit", type=int, default=25, help="maximum entries to print (default 25)")
    p_search.set_defaults(func=cmd_search)

    p_fetch = sub.add_parser(
        "fetch",
        help="print a page as text; with a symbol name or #anchor, print only that symbol's or section's text",
    )
    p_fetch.add_argument(
        "target",
        help="page path (learn/sdk), URL under https://docs.roboto.ai/, page#anchor, or an inventory name (roboto.Dataset.from_id)",
    )
    p_fetch.add_argument("--max-chars", type=int, default=20000, help="truncate output after this many characters (0 = no limit)")
    p_fetch.add_argument("--refresh", action="store_true", default=argparse.SUPPRESS, help=refresh_help)
    p_fetch.set_defaults(func=cmd_fetch)

    p_versions = sub.add_parser(
        "versions",
        help="compare the SDK release the references were checked against with the latest release and the installed CLI",
    )
    p_versions.set_defaults(func=cmd_versions)

    p_env = sub.add_parser(
        "env",
        help="print platform, shell, Python, uv, roboto CLI, credential presence, and the runner to use; prints no secret",
    )
    p_env.set_defaults(func=cmd_env)

    p_restapi = sub.add_parser(
        "restapi",
        help="list REST API endpoints matching every term, or with --path print one endpoint's parameters and schemas",
    )
    p_restapi.add_argument("terms", nargs="*", help="every term must appear in the endpoint's path, tag, operation ID, or summary")
    p_restapi.add_argument("--path", help="print this endpoint in full, for example /v1/layouts/create")
    p_restapi.add_argument("--method", help="with --path, print only this HTTP method")
    p_restapi.add_argument("--max-chars", type=int, default=20000, help="truncate output after this many characters (0 = no limit)")
    p_restapi.add_argument("--refresh", action="store_true", default=argparse.SUPPRESS, help="download restapi.html again even if the cached copy is less than 24 hours old")
    p_restapi.set_defaults(func=cmd_restapi)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
