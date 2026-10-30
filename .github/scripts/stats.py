"""Draws assets/stats.svg — GitHub numbers, top languages and the contribution
calendar — in the same terminal style as assets/terminal.svg.

Runs daily from .github/workflows/stats.yml. Uses only the standard library.
Local run:  GITHUB_TOKEN=$(gh auth token) python3 .github/scripts/stats.py
"""
import datetime as dt
import html
import json
import os
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "GorcevicHaris")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "stats.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"
HEAT = ["#161B22", "#3D2316", "#7A3E1D", "#C2602A", "#FFA657"]


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def streaks(days):
    today = dt.date.today().isoformat()
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    for d in reversed(days):
        if d["contributionCount"]:
            current += 1
        elif d["date"] == today and current == 0:
            continue  # today isn't over yet
        else:
            break
    return current, longest


def render(u):
    cc = u["contributionsCollection"]
    weeks = cc["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    current, longest = streaks(days)

    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]
            size, color = langs.get(n["name"], (0, n["color"] or "#8B949E"))
            langs[n["name"]] = (size + e["size"], color)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]

    rows = [
        ("Contributions", f'{cc["contributionCalendar"]["totalContributions"]:,}', "last 12 months"),
        ("Commits", f'{cc["totalCommitContributions"]:,}', "last 12 months"),
        ("Pull requests", f'{cc["totalPullRequestContributions"]:,}', "last 12 months"),
        ("Followers", f'{u["followers"]["totalCount"]:,}', ""),
        ("Public repos", f'{u["repositories"]["totalCount"]}', ""),
        ("Current streak", f"{current} days", ""),
        ("Longest streak", f"{longest} days", "last 12 months"),
    ]

    W, H = 1000, 500
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">',
         f'<title id="t">GitHub statistics for {LOGIN}</title>',
         f'<defs><clipPath id="win"><rect width="{W}" height="{H}" rx="14"/></clipPath></defs>',
         f'<g clip-path="url(#win)"><rect width="{W}" height="{H}" fill="#0D1117"/><rect width="{W}" height="44" fill="#161B22"/><path d="M0 44.5 H{W}" stroke="#30363D"/></g>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="#30363D"/>',
         '<circle cx="24" cy="22" r="6.5" fill="#FF5F57"/><circle cx="46" cy="22" r="6.5" fill="#FEBC2E"/><circle cx="68" cy="22" r="6.5" fill="#28C840"/>',
         f'<g font-family="{MONO}">',
         f'<text x="{W / 2}" y="27" text-anchor="middle" font-size="12.5" fill="#6E7681">haris@gorcevicharis: ~/stats</text>',
         '<text x="40" y="82" font-size="15"><tspan fill="#3FB950">➜</tspan><tspan fill="#58A6FF">  ~</tspan><tspan fill="#C9D1D9"> gh stats</tspan><tspan fill="#8B949E"> --user GorcevicHaris</tspan></text>']

    # numbers
    for i, (k, v, note) in enumerate(rows):
        y = 124 + i * 27
        o.append(f'<text x="40" y="{y}" font-size="14.5"><tspan fill="#FFA657">{k}</tspan>'
                 f'<tspan x="196" fill="#F0F6FC" font-weight="700">{html.escape(v)}</tspan>'
                 f'<tspan x="300" fill="#6E7681" font-size="12.5">{note}</tspan></text>')

    # languages
    LX, LW = 560, 400
    o.append(f'<text x="{LX}" y="124" font-size="14.5" fill="#FFA657">Top languages</text>')
    o.append(f'<text x="{LX + LW}" y="124" font-size="12.5" fill="#6E7681" text-anchor="end">public repos, by code size</text>')
    o.append(f'<clipPath id="bar"><rect x="{LX}" y="140" width="{LW}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    x = LX
    for name, (size, color) in top:
        w = LW * size / total
        o.append(f'<rect x="{x:.1f}" y="140" width="{w + 0.5:.1f}" height="10" fill="{color}"/>')
        x += w
    o.append(f'<rect x="{x:.1f}" y="140" width="{LX + LW - x + 1:.1f}" height="10" fill="#30363D"/></g>')
    for i, (name, (size, color)) in enumerate(top):
        cx, cy = LX + (i % 2) * 210, 180 + (i // 2) * 27
        o.append(f'<circle cx="{cx + 5}" cy="{cy - 4.5}" r="5" fill="{color}"/>'
                 f'<text x="{cx + 18}" y="{cy}" font-size="14"><tspan fill="#C9D1D9">{html.escape(name)}</tspan>'
                 f'<tspan x="{cx + 190}" text-anchor="end" fill="#8B949E">{100 * size / total:.1f}%</tspan></text>')

    # contribution calendar
    S, G = 13, 3.5
    gx = (W - len(weeks) * (S + G) + G) / 2
    gy = 330
    # GitHub-style levels: quartiles of the days that had any activity
    nz = sorted(d["contributionCount"] for d in days if d["contributionCount"])
    q = [nz[int(len(nz) * f)] for f in (0.25, 0.5, 0.75)] if nz else [1, 1, 1]
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = dt.date.fromisoformat(d["date"]).isoweekday() % 7
            n = d["contributionCount"]
            lvl = 0 if n == 0 else 1 + sum(n > t for t in q)
            o.append(f'<rect x="{gx + wi * (S + G):.1f}" y="{gy + wd * (S + G):.1f}" width="{S}" height="{S}" rx="3" fill="{HEAT[lvl]}"><title>{d["date"]}: {n}</title></rect>')
    ly = gy + 7 * (S + G) + 18
    o.append(f'<text x="{gx}" y="{ly}" font-size="12.5" fill="#8B949E">{cc["contributionCalendar"]["totalContributions"]:,} contributions in the last year · updated {dt.date.today():%d %b %Y}</text>')
    lx = W - gx - 5 * (S + G) - 74
    o.append(f'<text x="{lx}" y="{ly}" font-size="12.5" fill="#8B949E">less</text>')
    for i, c in enumerate(HEAT):
        o.append(f'<rect x="{lx + 36 + i * (S + G):.1f}" y="{ly - 11}" width="{S}" height="{S}" rx="3" fill="{c}"/>')
    o.append(f'<text x="{lx + 36 + 5 * (S + G) + 4:.1f}" y="{ly}" font-size="12.5" fill="#8B949E">more</text>')
    o.append("</g></svg>")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    svg = render(fetch())
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", os.path.normpath(OUT))
