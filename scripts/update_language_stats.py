#!/usr/bin/env python3
import json
import os
import sys
from html import escape
from urllib.error import HTTPError
from urllib.request import Request, urlopen


OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "MiguelLopesDel")
OUTPUT = "assets/language-stats.svg"
API = "https://api.github.com"

COLORS = {
    "Python": "#3572A5",
    "Java": "#b07219",
    "Rust": "#dea584",
    "JavaScript": "#f1e05a",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "C": "#555555",
    "C++": "#f34b7d",
    "TypeScript": "#3178c6",
    "Kotlin": "#A97BFF",
    "Go": "#00ADD8",
    "Dockerfile": "#384d54",
}


def request_json(path):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "language-stats-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(f"{API}{path}", headers=headers)
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API failed for {path}: {exc.code} {body}") from exc


def list_repositories():
    repos = []
    page = 1
    while True:
        batch = request_json(f"/users/{OWNER}/repos?per_page=100&type=owner&page={page}")
        if not batch:
            return repos
        repos.extend(repo for repo in batch if not repo.get("fork"))
        page += 1


def collect_languages(repos):
    totals = {}
    for repo in repos:
        languages = request_json(f"/repos/{OWNER}/{repo['name']}/languages")
        for language, size in languages.items():
            totals[language] = totals.get(language, 0) + int(size)
    return totals


def percentage_rows(totals):
    total = sum(totals.values())
    if total == 0:
        raise RuntimeError("No language data returned by GitHub.")

    rows = []
    for language, size in sorted(totals.items(), key=lambda item: item[1], reverse=True):
        rows.append((language, size, size * 100 / total))

    top = rows[:6]
    other_percent = sum(percent for _, _, percent in rows[6:])
    if other_percent:
        top.append(("Outras", 0, other_percent))
    return top


def render_svg(rows):
    width = 720
    height = 360
    label_x = 32
    bar_x = 138
    bar_width = 520
    percent_x = 612
    first_y = 112
    gap = 34

    parts = [
        '<svg width="720" height="360" viewBox="0 0 720 360" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">',
        '  <title id="title">Linguagens mais usadas</title>',
        '  <desc id="desc">Grafico com percentuais de linguagens usadas nos repositorios publicos.</desc>',
        '  <rect width="720" height="360" rx="12" fill="#1a1b27"/>',
        '  <text x="32" y="42" fill="#70a5fd" font-family="Segoe UI, Ubuntu, sans-serif" font-size="22" font-weight="700">Linguagens mais usadas</text>',
        '  <text x="32" y="68" fill="#a9b1d6" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">Distribuicao por linguagem</text>',
        "",
        '  <g font-family="Segoe UI, Ubuntu, sans-serif" font-size="14">',
    ]

    for index, (language, _, percent) in enumerate(rows):
        y = first_y + index * gap
        rect_y = y - 15
        color = COLORS.get(language, "#8fbcbb")
        fill_width = round(bar_width * percent / 100, 1)
        parts.extend(
            [
                f'    <text x="{label_x}" y="{y}" fill="#c0caf5">{escape(language)}</text>',
                f'    <rect x="{bar_x}" y="{rect_y}" width="{bar_width}" height="20" rx="10" fill="#24283b"/>',
                f'    <rect x="{bar_x}" y="{rect_y}" width="{fill_width}" height="20" rx="10" fill="{color}"/>',
                f'    <text x="{percent_x}" y="{y}" fill="#c0caf5" text-anchor="end">{percent:.2f}%</text>',
                "",
            ]
        )

    parts.extend(["  </g>", "</svg>", ""])
    return "\n".join(parts)


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    repos = list_repositories()
    rows = percentage_rows(collect_languages(repos))
    svg = render_svg(rows)

    current = None
    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r", encoding="utf-8") as file:
            current = file.read()
    if current == svg:
        print(f"{OUTPUT} is already up to date.")
        return 0

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)
    print(f"Updated {OUTPUT}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
