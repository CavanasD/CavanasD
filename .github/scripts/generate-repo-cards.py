#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html import escape
from pathlib import Path


OWNER = "CavanasD"
REPOS = [
    {
        "name": "ThesisDrive",
        "tagline": "Pinned project",
        "description": "A UESTC freshman innovation project about cloud-drive attack and defense.",
        "accent": "#7ee787",
    },
    {
        "name": "Java-easy-tutorial",
        "tagline": "Learning notes",
        "description": "Java notes and source code collected along my learning journey.",
        "accent": "#f0883e",
    },
]

OUT_DIR = Path(".github/cards")

LANG_COLORS = {
    "Vue": "#41b883",
    "Java": "#b07219",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C": "#555555",
    "C++": "#f34b7d",
    "Rust": "#dea584",
    "Kotlin": "#A97BFF",
}

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "title": "#c9d1d9",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "link": "#58a6ff",
        "chip_bg": "#161b22",
        "chip_border": "#30363d",
        "shadow": "#000000",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "title": "#24292f",
        "text": "#24292f",
        "muted": "#57606a",
        "link": "#0969da",
        "chip_bg": "#f6f8fa",
        "chip_border": "#d0d7de",
        "shadow": "#6e7781",
    },
}


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CavanasD-profile-card-generator",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def fetch_repo(repo):
    base = f"https://api.github.com/repos/{OWNER}/{repo['name']}"
    data = request_json(base)
    languages = request_json(data["languages_url"])
    return data, languages


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def human_date(value):
    if not value:
        return "unknown"
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m-%d")


def format_count(value):
    value = int(value or 0)
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def measure(text):
    width = 0.0
    for ch in text:
        if ord(ch) > 255:
            width += 1.0
        elif ch in "il.,:;|!":
            width += 0.32
        elif ch in " mwMW@#%&":
            width += 0.78
        else:
            width += 0.58
    return width


def wrap_text(text, limit=44, max_lines=2):
    text = " ".join((text or "").split())
    if not text:
        return []
    lines = []
    current = ""
    for part in re.findall(r"[\u4e00-\u9fff]|[^\s\u4e00-\u9fff]+", text):
        candidate = current + ("" if not current or len(part) == 1 and ord(part[0]) > 255 else " ") + part
        if measure(candidate) <= limit:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = part
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and measure(lines[-1]) > limit - 1:
        while lines[-1] and measure(lines[-1] + "...") > limit:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."
    elif len(lines) == max_lines and len("".join(lines)) < len(text.replace(" ", "")):
        while lines[-1] and measure(lines[-1] + "...") > limit:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."
    return lines


def top_languages(languages, max_items=3):
    total = sum(languages.values())
    if not total:
        return []
    return [
        (name, count / total)
        for name, count in sorted(languages.items(), key=lambda item: item[1], reverse=True)[:max_items]
    ]


def render_card(repo_config, repo, languages, theme_name):
    theme = THEMES[theme_name]
    accent = repo_config["accent"]
    title = repo["name"]
    description = repo_config.get("description") or repo.get("description") or repo_config["tagline"]
    language = repo.get("language") or "Code"
    language_color = LANG_COLORS.get(language, accent)
    updated = human_date(repo.get("pushed_at") or repo.get("updated_at"))
    lang_items = top_languages(languages)
    desc_lines = wrap_text(description)

    lang_bar = ""
    cursor = 24
    for name, ratio in lang_items:
        width = max(20, round(380 * ratio))
        color = LANG_COLORS.get(name, "#8b949e")
        lang_bar += f'<rect x="{cursor}" y="114" width="{width}" height="8" rx="4" fill="{color}"/>'
        cursor += width

    chips = []
    chip_x = 24
    for label, value in [
        ("stars", format_count(repo.get("stargazers_count"))),
        ("forks", format_count(repo.get("forks_count"))),
        ("issues", format_count(repo.get("open_issues_count"))),
        ("pushed", updated),
    ]:
        text = f"{label} {value}"
        chip_width = max(62, int(10 + measure(text) * 8.5))
        chips.append(
            f'<g><rect x="{chip_x}" y="142" width="{chip_width}" height="25" rx="12.5" '
            f'fill="{theme["chip_bg"]}" stroke="{theme["chip_border"]}"/>'
            f'<text x="{chip_x + 12}" y="159" fill="{theme["muted"]}" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12">{escape(text)}</text></g>'
        )
        chip_x += chip_width + 8

    desc_svg = []
    for idx, line in enumerate(desc_lines):
        desc_svg.append(
            f'<text x="24" y="{71 + idx * 19}" fill="{theme["text"]}" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="14">{escape(line)}</text>'
        )

    repo_path = f"{OWNER}/{title}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="190" viewBox="0 0 520 190" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
    <filter id="shadow" x="-10%" y="-20%" width="120%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="{theme["shadow"]}" flood-opacity="0.12"/>
    </filter>
  </defs>
  <rect x="1" y="1" width="518" height="188" rx="8" fill="{theme["bg"]}" stroke="{theme["border"]}" filter="url(#shadow)"/>
  <circle cx="28" cy="32" r="8" fill="{language_color}"/>
  <text x="48" y="39" fill="{theme["link"]}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="22" font-weight="700">{escape(title)}</text>
  <text x="24" y="55" fill="{theme["muted"]}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12">{escape(repo_path)} · {escape(repo_config["tagline"])}</text>
  {''.join(desc_svg)}
  <rect x="24" y="114" width="380" height="8" rx="4" fill="{theme["chip_bg"]}"/>
  {lang_bar}
  <text x="418" y="122" fill="{theme["muted"]}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12">{escape(language)}</text>
  {''.join(chips)}
</svg>
'''


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for repo_config in REPOS:
        repo, languages = fetch_repo(repo_config)
        base = slug(repo_config["name"])
        for theme_name in THEMES:
            svg = render_card(repo_config, repo, languages, theme_name)
            (OUT_DIR / f"{base}-{theme_name}.svg").write_text(svg, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"GitHub API error: {exc.code} {exc.reason}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise
