import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

URL = "https://www.tcgplayer.com/content/"

# Categorías conocidas que aparecen pegadas delante del título
KNOWN_CATEGORIES = [
    "Magic: The Gathering",
    "Disney Lorcana",
    "Flesh and Blood",
    "Star Wars: Unlimited",
    "Dragon Ball Super: Fusion World",
    "Shadowverse: Evolve",
    "Sorcery: Contested Realm",
    "Cardfight!! Vanguard",
    "Grand Archive TCG",
    "Gundam Card Game",
    "Digimon Card Game",
    "One Piece",
    "Yu-Gi-Oh!",
    "Riftbound",
    "Pokémon",
]


def clean_title(raw_title):
    text = raw_title

    # 1. Quitar la categoría pegada al principio
    for cat in KNOWN_CATEGORIES:
        if text.startswith(cat):
            text = text[len(cat):]
            break

    # 2. Quitar "Read Now" pegado al final
    text = re.sub(r"Read Now$", "", text)

    # 3. Quitar "By<Autor>" pegado al final
    text = re.sub(r"By[A-ZÀ-Ý][\wÀ-ÿ'\.]*(?:\s[A-ZÀ-Ý][\wÀ-ÿ'\.]*)*$", "", text)

    return text.strip()


fg = FeedGenerator()
fg.title("TCGplayer Infinite Content")
fg.link(href=URL, rel="alternate")
fg.description("Últimas noticias y artículos de TCGplayer")

html = ""
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()
except Exception as e:
    print(f"Error al conectar con la web: {e}")

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
                fe.title(clean_title(title))
                fe.link(href=link)
                fe.id(link)
                articles_found = True
    except Exception as e:
        print(f"Error parseando JSON: {e}")

# 2. Si no viene en __NEXT_DATA__, buscar directamente los enlaces en el HTML ya renderizado
if not articles_found and html:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=True)
    seen = set()
    for a in links:
        href = a["href"]
        raw_title = a.get_text(strip=True)
        if (
            "/content/article/" in href
            and href not in seen
            and len(raw_title) > 15
        ):
            seen.add(href)
            full_url = (
                href if href.startswith("http") else f"https://www.tcgplayer.com{href}"
            )
            fe = fg.add_entry()
            fe.title(clean_title(raw_title))
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
print(f"Archivo feed.xml generado. Articulos encontrados: {articles_found}")
