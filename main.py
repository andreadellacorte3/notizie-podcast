import os
import sys
from datetime import datetime

from config import (
    TELEGRAM_URL, MAX_POST, VOCE, VELOCITA,
    OUTPUT_DIR, LINGUA_SORGENTE, LINGUA_TARGET
)
from scraper import fetch_posts
from traduttore import traduci_lista
from generatore_audio import costruisci_script, genera_audio
from generatore_html import genera_html


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def main():
    oggi = datetime.now()
    data_str = oggi.strftime("%d %B %Y").lower()
    prefisso = oggi.strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Scarica i post
    log(f"Scarico notizie da {TELEGRAM_URL}...")
    try:
        posts = fetch_posts(TELEGRAM_URL, MAX_POST)
    except RuntimeError as e:
        log(f"ERRORE: {e}")
        sys.exit(1)

    if not posts:
        log("Nessun post trovato. Il canale potrebbe essere privato o irraggiungibile.")
        sys.exit(1)

    log(f"Trovati {len(posts)} post.")

    # 2. Traduci
    log("Traduco in italiano...")
    posts_tradotti = traduci_lista(posts, LINGUA_SORGENTE, LINGUA_TARGET)

    # 3. Genera audio
    nome_audio = f"notizie_{prefisso}.mp3"
    path_audio = os.path.join(OUTPUT_DIR, nome_audio)
    log("Genero podcast audio...")
    script = costruisci_script(posts_tradotti, data_str)
    tempi_articoli = genera_audio(script, path_audio, VOCE, VELOCITA, len(posts_tradotti))
    log(f"Audio salvato: {path_audio}")
    if tempi_articoli:
        log(f"Timing acquisito per {len(tempi_articoli)} articoli.")

    # 4. Genera pagina HTML
    nome_html = f"notizie_{prefisso}.html"
    path_html = os.path.join(OUTPUT_DIR, nome_html)
    html = genera_html(posts_tradotti, data_str, nome_audio, tempi_articoli)
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"Pagina HTML salvata: {path_html}")

    # 5. Crea/aggiorna indice (link all'ultimo aggiornamento)
    path_indice = os.path.join(OUTPUT_DIR, "index.html")
    with open(path_indice, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={nome_html}">
<title>Reindirizzamento...</title>
</head>
<body>
<a href="{nome_html}">Apri ultime notizie ({data_str})</a>
</body>
</html>""")

    log("Fatto! Apri OneDrive sul telefono e cerca la cartella 'Notizie Podcast'.")
    log(f"  Leggi: {nome_html}")
    log(f"  Ascolta: {nome_audio}")


if __name__ == "__main__":
    main()
