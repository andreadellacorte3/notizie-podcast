import requests
from bs4 import BeautifulSoup
from datetime import datetime


def fetch_posts(url, max_post):
    """
    Scarica i post recenti da un canale Telegram pubblico.
    Non richiede account o API key.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Impossibile raggiungere il canale Telegram: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    messaggi = soup.select(".tgme_widget_message_wrap")

    posts = []
    for msg in messaggi:
        # Testo del messaggio
        testo_el = msg.select_one(".tgme_widget_message_text")
        if not testo_el:
            continue

        testo = testo_el.get_text(separator="\n").strip()
        if not testo or len(testo) < 20:
            continue

        # Data del messaggio (se presente)
        data_el = msg.select_one("time")
        data_str = ""
        if data_el and data_el.get("datetime"):
            try:
                dt = datetime.fromisoformat(data_el["datetime"].replace("Z", "+00:00"))
                data_str = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                pass

        posts.append({"testo": testo, "data": data_str})

    # Restituisce gli ultimi N post (i più recenti sono in fondo)
    return posts[-max_post:]
