import re
import time
import random
import json
from urllib.parse import urljoin, urlparse, parse_qs, urlparse as uparse, quote
from http.server import BaseHTTPRequestHandler

import requests
from bs4 import BeautifulSoup

BASE = "https://modyolo.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Mobile Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/",
}


def fetch(url: str) -> str:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        r = s.get(url, timeout=20)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    proxied = "https://api.allorigins.win/raw?url=" + quote(url, safe="")
    r = requests.get(proxied, timeout=30)
    r.raise_for_status()
    return r.text


def get_download_links(app_page_url: str):
    html = fetch(app_page_url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    app_title = title_tag.get_text(" ", strip=True) if title_tag else ""

    download_page = None
    for a in soup.find_all("a", href=True):
        if "/download/" in a["href"]:
            download_page = urljoin(BASE, a["href"])
            break
    if not download_page:
        return {"error": "No /download/ link on app page"}

    time.sleep(random.uniform(0.5, 1.5))
    html2 = fetch(download_page)
    soup2 = BeautifulSoup(html2, "html.parser")

    options = []
    direct_apk = None

    for a in soup2.find_all("a", href=True):
        href = a["href"].strip()
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        full = urljoin(BASE, href)
        host = urlparse(full).netloc.lower()

        if host and "modyolo.com" not in host and "files" not in host:
            continue
        if "t.me" in host or "facebook" in host or "twitter" in host:
            continue
        if "/cdn-cgi/" in href:
            continue
        if not text.lower().startswith("download"):
            continue

        if "files" in host:
            kind = "file"
            if full.lower().endswith(".apk"):
                kind = "apk"
                direct_apk = full
            elif full.lower().endswith(".xapk"):
                kind = "xapk"
        elif "/download/" in full:
            kind = "page"
        else:
            continue

        options.append({"type": kind, "label": text, "url": full, "host": host})

    return {
        "app": app_title,
        "download_page": download_page,
        "direct_apk": direct_apk,
        "all_options": options,
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(uparse(self.path).query)
        app_url = (params.get("url", [""])[0] or "").strip()

        p = urlparse(app_url) if app_url else None
        if (not app_url
                or "modyolo.com" not in (p.netloc if p else "")
                or not p.path.endswith(".html")):
            body = json.dumps({
                "error": "Provide ?url=https://modyolo.com/<app>.html",
                "example": "/api/download?url=https://modyolo.com/whatsapp-messenger.html",
            })
            status = 400
        else:
            try:
                body = json.dumps(get_download_links(app_url), ensure_ascii=False)
                status = 200
            except Exception as e:
                body = json.dumps({"error": str(e)})
                status = 500

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
