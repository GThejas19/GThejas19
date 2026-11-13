
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "GThejas19"
OUTPUT = Path("profile/contribution-graph.svg")

TOKEN = os.environ.get("GH_TOKEN")

if not TOKEN:
    raise RuntimeError("GH_TOKEN secret is missing.")

end_date = datetime.now(timezone.utc).date()
start_date = end_date - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": start_date.isoformat() + "T00:00:00Z",
        "to": end_date.isoformat() + "T23:59:59Z"
    }
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "GitHub-Contribution-Graph"
    },
    method="POST"
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read().decode("utf-8"))

if result.get("errors"):
    raise RuntimeError(
        "GitHub GraphQL error: " + json.dumps(result["errors"])
    )

user = result.get("data", {}).get("user")

if not user:
    raise RuntimeError("GitHub user was not found.")

calendar = user["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

# SVG dimensions
cell = 12
gap = 4
step = cell + gap
left = 48
top = 55
width = left + len(weeks) * step + 20
height = 170

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="100%" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" rx="12" fill="#080B20"/>',
    '<style>',
    'text{font-family:Arial,sans-serif;fill:#C9D1D9}',
    '.heading{font-size:18px;font-weight:bold;fill:#FFFFFF}',
    '.sub{font-size:11px;fill:#9CA3AF}',
    '.day{font-size:9px;fill:#8B949E}',
    '</style>',
    '<text x="20" y="27" class="heading">Contribution Activity</text>',
    f'<text x="20" y="43" class="sub">'
    f'{total} contributions in the last year</text>'
]

# Day labels
for i, day in enumerate(days):
    if i % 2 == 0:
        y = top + i * step + 10
        svg.append(
            f'<text x="8" y="{y}" class="day">{day}</text>'
        )

# Contribution squares and month labels
last_month = None

for week_index, week in enumerate(weeks):
    x = left + week_index * step

    for day in week["contributionDays"]:
        date = datetime.strptime(day["date"], "%Y-%m-%d").date()
        weekday = date.weekday()
        y = top + weekday * step

        color = day.get("color") or "#161B22"
        count = day["contributionCount"]

        svg.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="3" fill="{escape(color)}">'
            f'<title>{day["date"]}: {count} contributions</title>'
            f'</rect>'
        )

        if date.month != last_month and weekday <= 3:
            svg.append(
                f'<text x="{x}" y="50" class="day">'
                f'{date.strftime("%b")}</text>'
            )
            last_month = date.month

# Legend
legend_y = top + 7 * step + 12
svg.append(
    f'<text x="{left}" y="{legend_y}" class="day">Less</text>'
)

legend_colors = [
    "#161B22",
    "#0E4429",
    "#006D32",
    "#26A641",
    "#39D353"
]

for i, color in enumerate(legend_colors):
    x = left + 35 + i * 18
    svg.append(
        f'<rect x="{x}" y="{legend_y - 9}" width="11" '
        f'height="11" rx="2" fill="{color}"/>'
    )

svg.append(
    f'<text x="{left + 135}" y="{legend_y}" class="day">More</text>'
)

svg.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(svg), encoding="utf-8")

print(f"Contribution graph generated: {OUTPUT}")
