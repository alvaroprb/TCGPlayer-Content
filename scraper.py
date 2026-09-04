import json
import re
from feedgen.feed import FeedGenerator
import requests

URL = "https://www.tcgplayer.com/content/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": (
        '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

fg = FeedGenerator()
fg.title("TCGplayer Infinite Content")
fg.link(href=URL, rel="alternate")
fg.description("Últimas noticias y artículos de TCGplayer")

try:
  res = requests.get(URL, headers=HEADERS, timeout=30)
  html = res.text
except Exception as e:
  print(f"Error al conectar con la web: {e}")
  html = ""

articles_found = False

match = re.search(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html
)
if match:
  try:
    data = json.loads(match.group(1))
    page_props = data.get("props", {}).get("pageProps", {})
    posts = (
        page_props.get("articles")
        or page_props.get("posts")
        or page_props.get("latestArticles", [])
    )
    for post in posts[:20]:
      title = post.get("title")
      slug = post.get("slug") or post.get("url", "")
      if title and slug:
        link = (
            slug
            if slug.startswith("http")
            else f"https://www.tcgplayer.com/content{slug}"
        )
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.id(link)
        articles_found = True
  except Exception:
    pass

if not articles_found and html:
  from bs4 import BeautifulSoup

  soup = BeautifulSoup(html, "html.parser")
  links = soup.find_all("a", href=True)
  seen = set()
  for a in links:
    href = a["href"]
    title = a.get_text(strip=True)
    if (
        ("/article/" in href or "/content/" in href)
        and href not in seen
        and len(title) > 12
    ):
      seen.add(href)
      full_url = (
          href if href.startswith("http") else f"https://www.tcgplayer.com{href}"
      )
      fe = fg.add_entry()
      fe.title(title)
      fe.link(href=full_url)
      fe.id(full_url)
      articles_found = True

if not articles_found:
  fe = fg.add_entry()
  fe.title("Feed inicializado - Esperando primera actualización de artículos")
  fe.link(href=URL)
  fe.id(URL)

fg.rss_file("feed.xml")
print("Archivo feed.xml generado correctamente.")
