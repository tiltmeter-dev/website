#!/usr/bin/env python3
"""The site's shell, in one place: what every page loads, its navigation and its footer.

Hand-written pages carry three marked blocks that this script rewrites:

    <!-- shell:head:start --> ... <!-- shell:head:end -->   fonts, stylesheets, the js class
    <!-- shell:nav:start -->  ... <!-- shell:nav:end -->    skip link and navigation
    <!-- shell:foot:start --> ... <!-- shell:foot:end -->   footer

scripts/migrations.py imports head(), nav() and foot() for the pages it generates, so every
page shows the same navigation. Rerun after changing anything here:

    python3 scripts/shell.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GITHUB = "https://github.com/tiltmeter-dev/tiltmeter"
DOCS = f"{GITHUB}/blob/main/docs/getting-started.md"
NOTICE_SPEC = f"{GITHUB}/blob/main/docs/notice-spec.md"
ACTION = "https://github.com/tiltmeter-dev/tiltmeter-action"

# What happens next: an email to us, with the three facts we need already asked for.
SEND = (
    "mailto:hello@tiltmeter.dev?subject=Our%20next%20deprecation&amp;body="
    "What%20is%20changing%20(endpoint%2C%20model%20or%20field)%3A%0D%0A%0D%0A"
    "When%20it%20takes%20effect%3A%0D%0A%0D%0A"
    "Link%20to%20the%20announcement%20or%20docs%3A%0D%0A"
)

LOGO = (
    '<svg viewBox="0 0 1024 1024" aria-hidden="true"><rect width="1024" height="1024" rx="224" '
    'fill="#f2efe7"/><path d="M487 230V651Q487 776 612 776H674" fill="none" stroke="#141416" '
    'stroke-width="100" stroke-linecap="round" stroke-linejoin="round"/><path d="M323 425H682" '
    'stroke="#e2552d" stroke-width="100" stroke-linecap="round" transform="rotate(-13 487 425)"/></svg>'
)

NAV_ITEMS = [
    ("how", "/#how", "How it works"),
    ("evidence", "/migrations/", "Evidence"),
    ("security", "/#security", "Security"),
    ("pricing", "/#pricing", "Pricing"),
    ("docs", DOCS, "Docs"),
]

PAGES = {
    # path: (current nav item, extra stylesheets after the shell's)
    "index.html": ("", ["/home.css"]),
    "developers/index.html": ("", []),
}


def head(extra: list[str] | None = None) -> str:
    sheets = "".join(f'\n  <link rel="stylesheet" href="{href}">' for href in ["/styles.css", "/tokens.css", "/site.css", *(extra or [])])
    return (
        '<!-- shell:head:start -->\n'
        '  <script>document.documentElement.classList.add("js")</script>\n'
        '  <link rel="preload" href="/fonts/schibsted-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
        '  <link rel="preload" href="/fonts/ibm-plex-mono-400-latin.woff2" as="font" type="font/woff2" crossorigin>'
        f'{sheets}\n'
        '  <script src="/site.js" defer></script>\n'
        '  <!-- shell:head:end -->'
    )


def nav(current: str = "") -> str:
    mark = ' aria-current="page"'
    items = "\n".join(
        f'          <li><a href="{href}"{mark if key == current else ""}>{label}</a></li>'
        for key, href, label in NAV_ITEMS
    )
    return f"""<!-- shell:nav:start -->
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-nav">
    <div class="site-nav__in page">
      <a class="site-brand" href="/" aria-label="Tiltmeter, home">{LOGO}<span aria-hidden="true">tiltmeter</span></a>
      <button class="site-nav__toggle" type="button" aria-expanded="false" aria-controls="site-menu">Menu</button>
      <nav class="site-nav__menu" id="site-menu" aria-label="Main">
        <ul class="site-nav__links">
{items}
        </ul>
        <a class="button button--line site-nav__cta" href="{SEND}">Send a deprecation</a>
      </nav>
    </div>
  </header>
  <!-- shell:nav:end -->"""


def foot() -> str:
    return f"""<!-- shell:foot:start -->
  <footer class="site-foot">
    <div class="page">
      <div class="site-foot__in">
        <div class="site-foot__about">
          <a class="site-brand" href="/" aria-label="Tiltmeter, home">{LOGO}<span aria-hidden="true">tiltmeter</span></a>
          <p>API changes, shipped as pull requests in the code that still uses them.</p>
          <a class="link" href="mailto:hello@tiltmeter.dev">hello@tiltmeter.dev</a>
        </div>
        <nav class="site-foot__cols" aria-label="Footer">
          <div>
            <h2>Product</h2>
            <ul>
              <li><a href="/#how">How it works</a></li>
              <li><a href="/migrations/">Evidence</a></li>
              <li><a href="/#security">Security</a></li>
              <li><a href="/#pricing">Pricing</a></li>
              <li><a href="{NOTICE_SPEC}">Notice format</a></li>
            </ul>
          </div>
          <div>
            <h2>Developers</h2>
            <ul>
              <li><a href="/developers/">Tiltmeter for developers</a></li>
              <li><a href="{DOCS}">Docs</a></li>
              <li><a href="{ACTION}">GitHub Action</a></li>
              <li><a href="https://pypi.org/project/tiltmeter/">PyPI</a></li>
              <li><a href="/llms.txt">llms.txt</a></li>
            </ul>
          </div>
          <div>
            <h2>Open source</h2>
            <ul>
              <li><a href="{GITHUB}">GitHub</a></li>
              <li><a href="{GITHUB}/blob/main/CHANGELOG.md">Changelog</a></li>
              <li><a href="{GITHUB}/blob/main/SECURITY.md">Security policy</a></li>
              <li><a href="/migrations/status.json">Tracker data (JSON)</a></li>
            </ul>
          </div>
        </nav>
      </div>
      <div class="site-foot__base">
        <p>© 2026 Tiltmeter</p>
        <p>Open-source core, MIT</p>
        <p>Claude and Codex are trademarks of Anthropic and OpenAI. Tiltmeter is not affiliated with either.</p>
      </div>
    </div>
  </footer>
  <!-- shell:foot:end -->"""


def replace(html: str, name: str, block: str, path: str) -> str:
    html, count = re.subn(rf"<!-- shell:{name}:start -->.*?<!-- shell:{name}:end -->", lambda _: block, html, flags=re.S)
    if count != 1:
        raise SystemExit(f"{path} needs one <!-- shell:{name}:start --> ... <!-- shell:{name}:end --> block")
    return html


def main() -> None:
    for path, (current, extra) in PAGES.items():
        page = ROOT / path
        html = page.read_text(encoding="utf-8")
        html = replace(html, "head", head(extra), path)
        html = replace(html, "nav", nav(current), path)
        html = replace(html, "foot", foot(), path)
        page.write_text(html, encoding="utf-8")
        print(f"{path}: shell written")


if __name__ == "__main__":
    main()
