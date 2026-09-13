import json
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

URL = "https://www.tcgplayer.com/content/"

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
    for cat in KNOWN_CATEGORIES:
        if text.startswith(cat):
            text = text[len(cat):]
            break
    text = re.sub(r"Read Now$", "", text)
    text = re.sub(r"By[A-ZÀ-Ý][\wÀ-ÿ'\.]*(?:\s[A-ZÀ-Ý][\wÀ-ÿ'\.]*)*$", "", text)
    return text.strip()


def extract_article_content(page, url):
    """Visita el artículo y devuelve su contenido en HTML."""
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        article_html = page.content()
        soup = BeautifulSoup(article_html, "html.parser")

        # Intentamos localizar el cuerpo del artículo por etiquetas típicas
        body = (
            soup.find("article")
            or soup.find("div", class_=re.compile("article-body|content-body|post-content", re.I))
            or soup.find("main")
        )
        if body:
            # Quitamos scripts/estilos residuales
            for tag in body.find_all(["script", "style"]):
                tag.decompose()
            return str(body)
        return ""
    except Exception as e:
        print(f"Error extrayendo contenido de {url}: {e}")
        return ""


fg = FeedGenerator()
fg.title("TCGplayer Infinite Content")
fg.link(href=URL, rel="alternate")
fg.description("Últimas noticias y artículos de TCGplayer")

html = ""
articles_found = False
entries = []

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        html = page.content()

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
                entries.append({"title": clean_title(raw_title), "link": full_url})

        # Para cada artículo encontrado, entramos a por el contenido completo
        for entry in entries[:15]:  # límite para no alargar demasiado el workflow
            content_html = extract_article_content(page, entry["link"])
            entry["content"] = content_html
            time.sleep(1)  # pequeña pausa entre peticiones

        browser.close()
except Exception as e:
    print(f"Error al conectar con la web: {e}")

for entry in entries:
    fe = fg.add_entry()
    fe.title(entry["title"])
    fe.link(href=entry["link"])
    fe.id(entry["link"])
    if entry.get("content"):
        fe.content(entry["content"], type="CDATA")
        articles_found = True
    else:
        fe.description("No se pudo extraer el contenido completo. Lee el artículo en el enlace.")

if not articles_found and not entries:
    fe = fg.add_entry()
    fe.title("Feed inicializado - Esperando primera actualización de artículos")
    fe.link(href=URL)
    fe.id(URL)

fg.rss_file("feed.xml")
print(f"Archivo feed.xml generado. Articulos encontrados: {len(entries)}")
