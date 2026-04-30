"""
Script autonomo per GitHub Actions.
Scarica, traduce e genera il podcast senza dipendenze esterne tranne
requests, beautifulsoup4 e edge-tts (installati nel workflow).
"""

import asyncio
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup
import edge_tts

# ── Configurazione ──────────────────────────────────────────
TELEGRAM_URL = "https://t.me/s/evropar"
MAX_POST = 15
VOCE = "it-IT-ElsaNeural"
VELOCITA = "+5%"
OUTPUT_DIR = "docs"
# ────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def log(msg):
    ora = datetime.now().strftime("%H:%M:%S")
    print(f"[{ora}] {msg}", flush=True)


# ── Scraping ────────────────────────────────────────────────

def fetch_posts():
    resp = requests.get(TELEGRAM_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []
    for msg in soup.select(".tgme_widget_message_wrap"):
        el = msg.select_one(".tgme_widget_message_text")
        if not el:
            continue
        testo = el.get_text(separator="\n").strip()
        if len(testo) < 20:
            continue
        data_el = msg.select_one("time")
        data_str = ""
        if data_el and data_el.get("datetime"):
            try:
                dt = datetime.fromisoformat(data_el["datetime"].replace("Z", "+00:00"))
                data_str = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                pass
        posts.append({"testo": testo, "data": data_str})
    return posts[-MAX_POST:]


# ── Traduzione ──────────────────────────────────────────────

def rimuovi_emoji(testo):
    return re.sub(
        r"[\U0001F300-\U0001F9FF\U00002702-\U000027B0\u2600-\u27BF]+",
        " ", testo, flags=re.UNICODE
    ).strip()


def _traduci_blocco(blocco):
    """Traduce un singolo blocco di max 490 caratteri."""
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": blocco, "langpair": "ru|it"},
            headers=HEADERS,
            timeout=15,
        )
        data = resp.json()
        if data.get("responseStatus") == 200:
            return data["responseData"]["translatedText"]
    except Exception:
        pass
    return blocco  # fallback: testo originale


def traduci(testo):
    testo = rimuovi_emoji(testo)
    if not testo.strip():
        return testo

    LIMITE = 490  # MyMemory accetta max 500 caratteri per richiesta

    # Se il testo è corto, traducilo direttamente
    if len(testo) <= LIMITE:
        return _traduci_blocco(testo)

    # Altrimenti spezza per frasi mantenendo il senso
    frasi = re.split(r'(?<=[.!?])\s+', testo)
    blocchi = []
    blocco_corrente = ""

    for frase in frasi:
        if len(blocco_corrente) + len(frase) + 1 <= LIMITE:
            blocco_corrente += (" " if blocco_corrente else "") + frase
        else:
            if blocco_corrente:
                blocchi.append(blocco_corrente)
            # Se la frase singola è troppo lunga, tagliala brutalmente
            while len(frase) > LIMITE:
                blocchi.append(frase[:LIMITE])
                frase = frase[LIMITE:]
            blocco_corrente = frase

    if blocco_corrente:
        blocchi.append(blocco_corrente)

    # Traduci ogni blocco con pausa per evitare rate limiting
    risultati = []
    for i, b in enumerate(blocchi):
        risultati.append(_traduci_blocco(b))
        if i < len(blocchi) - 1:
            time.sleep(0.4)

    return " ".join(risultati)


def traduci_lista(posts):
    risultato = []
    for i, post in enumerate(posts):
        log(f"  Traduzione {i + 1}/{len(posts)}...")
        tradotto = traduci(post["testo"])
        risultato.append({**post, "testo_tradotto": tradotto})
        time.sleep(0.5)
    return risultato


# ── Audio ───────────────────────────────────────────────────

def pulisci_tts(testo):
    testo = rimuovi_emoji(testo)
    testo = re.sub(r"https?://\S+", "", testo)
    testo = re.sub(r"\n{3,}", "\n\n", testo)
    return re.sub(r" {2,}", " ", testo).strip()


def costruisci_script(posts, data_str):
    parti = [f"Rassegna notizie del {data_str}. Canale Europea. {len(posts)} notizie."]
    for i, p in enumerate(posts, 1):
        testo = pulisci_tts(p.get("testo_tradotto") or p["testo"])
        if testo:
            parti.append(f"Notizia {i}. {testo}")
    parti.append("Fine della rassegna. Buona giornata.")
    return "\n\n".join(parti)


async def _genera_audio(testo, path, voce, velocita):
    await edge_tts.Communicate(testo, voce, rate=velocita).save(path)


def genera_audio(testo, path):
    asyncio.run(_genera_audio(testo, path, VOCE, VELOCITA))


# ── HTML ────────────────────────────────────────────────────

def genera_html(posts, data_str, nome_audio):
    notizie = ""
    for i, p in enumerate(posts, 1):
        testo = (p.get("testo_tradotto") or p["testo"]).replace("\n", "<br>")
        data_p = p.get("data", "")
        notizie += f"""
        <article>
            <div class="num">#{i}{f' <span class="data">{data_p}</span>' if data_p else ''}</div>
            <p>{testo}</p>
        </article>"""

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Notizie {data_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e8e8e8;padding:16px;max-width:700px;margin:0 auto}}
header{{padding:20px 0 16px;border-bottom:1px solid #333;margin-bottom:20px}}
h1{{font-size:1.1rem;color:#aaa;font-weight:400}}
h2{{font-size:1.5rem;color:#fff;margin-top:4px}}
.player{{background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:24px}}
.player p{{font-size:.85rem;color:#888;margin-bottom:10px}}
audio{{width:100%;border-radius:8px}}
article{{background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:14px}}
.num{{font-size:.75rem;color:#555;font-weight:600;margin-bottom:8px}}
.data{{color:#666;font-weight:400}}
article p{{font-size:.95rem;line-height:1.65;color:#ddd}}
footer{{text-align:center;color:#444;font-size:.75rem;padding:30px 0 16px}}
</style>
</head>
<body>
<header>
  <h1>Canale Europea — traduzione automatica</h1>
  <h2>{data_str}</h2>
</header>
<div class="player">
  <p>Ascolta (funziona in background con schermo spento)</p>
  <audio controls><source src="{nome_audio}" type="audio/mpeg">Audio non supportato.</audio>
</div>
{notizie}
<footer>Aggiornato automaticamente ogni mattina · {len(posts)} notizie</footer>
</body>
</html>"""


# ── Main ────────────────────────────────────────────────────

def main():
    # Ora italiana
    tz_it = timezone(timedelta(hours=2))
    oggi = datetime.now(tz_it)
    data_str = oggi.strftime("%-d %B %Y") if os.name != "nt" else oggi.strftime("%d/%m/%Y")
    prefisso = oggi.strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log(f"Scarico notizie da {TELEGRAM_URL}...")
    posts = fetch_posts()
    if not posts:
        log("Nessun post trovato.")
        return
    log(f"Trovati {len(posts)} post.")

    log("Traduco in italiano...")
    posts = traduci_lista(posts)

    nome_audio = f"notizie_{prefisso}.mp3"
    log("Genero audio...")
    genera_audio(costruisci_script(posts, data_str), f"{OUTPUT_DIR}/{nome_audio}")
    log("Audio generato.")

    nome_html = f"notizie_{prefisso}.html"
    with open(f"{OUTPUT_DIR}/{nome_html}", "w", encoding="utf-8") as f:
        f.write(genera_html(posts, data_str, nome_audio))
    log("HTML generato.")

    # index.html → reindirizza all'ultimo aggiornamento
    with open(f"{OUTPUT_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="it">
<head><meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={nome_html}">
<title>Notizie</title></head>
<body><a href="{nome_html}">Apri notizie del {data_str}</a></body>
</html>""")

    log(f"Fatto! File in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
