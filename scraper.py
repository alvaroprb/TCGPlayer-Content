import json
import re
from curl_cffi import requests
from feedgen.feed import FeedGenerator

URL = "https://www.tcgplayer.com/content/"

fg = FeedGenerator()
fg.title("TCGplayer Infinite Content")
fg.link(href=URL, rel="alternate")
fg.description("Últimas noticias y artículos de TCGplayer")

# curl_cffi simula a nivel de red un navegador Chrome real para evitar el antibot
try:
  res = requests.get(URL, impersonate="chrome120", timeout=30)
  html = res.text
except Exception as e:
  print(f"Error al conectar con la web: {e}")
  html = ""

articles_found = False

# 1. Intentar leer los datos internos del framework (Next/Nuxt)
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
        or page_props.get("latestArticles")
        or []
    )
    for post in posts[:25]:
      title = post.get("title") or post.get("headline")
      slug = post.get("slug") or post.get("url") or ""
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
  except Exception as e:
    print(f"Error parseando JSON: {e}")

# 2. Si no viene en __NEXT_DATA__, buscar directamente los enlaces en el HTML
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
        and len(title) > 15
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

# 3. Fallback en caso de que aún no extraiga datos
if not articles_found:
  fe = fg.add_entry()
  fe.title("Feed inicializado - Esperando primera actualización de artículos")
  fe.link(href=URL)
  fe.id(URL)

fg.rss_file("feed.xml")
print(
    f"Archivo feed.xml generado. Articulos encontrados: {articles_found}"
)
