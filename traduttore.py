import requests
import time


def _rimuovi_emoji(testo):
    """Rimuove emoji e caratteri speciali non gestiti dall'API."""
    import re
    # Rimuovi emoji (range Unicode comuni)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F9FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F004-\U0001F0CF"
        "\U0001F1E0-\U0001F1FF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(" ", testo).strip()


def _chiama_google(testo, target="it", retries=3):
    """Chiama l'endpoint pubblico di Google Translate senza API key."""
    testo = _rimuovi_emoji(testo)
    if not testo.strip():
        return testo

    url = "https://translate.googleapis.com/translate_a/single"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": testo,
    }
    for attempt in range(retries):
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            tradotto = "".join(part[0] for part in result[0] if part[0])
            if tradotto.strip():
                return tradotto
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"\n  [AVVISO] Traduzione fallita dopo {retries} tentativi: {e}")
    return testo  # fallback: testo originale


def traduci(testo, sorgente="auto", target="it"):
    """
    Traduce il testo usando Google Translate (gratuito, nessuna API key).
    Gestisce testi lunghi suddividendoli in blocchi.
    """
    if not testo or not testo.strip():
        return testo

    LIMITE = 4500

    if len(testo) <= LIMITE:
        return _chiama_google(testo, target)

    # Suddivide per paragrafi se il testo è troppo lungo
    paragrafi = testo.split("\n")
    risultato = []
    blocco = ""

    for paragrafo in paragrafi:
        if len(blocco) + len(paragrafo) + 1 <= LIMITE:
            blocco += paragrafo + "\n"
        else:
            if blocco.strip():
                risultato.append(_chiama_google(blocco.strip(), target))
            blocco = paragrafo + "\n"

    if blocco.strip():
        risultato.append(_chiama_google(blocco.strip(), target))

    return "\n".join(risultato)


def traduci_lista(posts, sorgente="auto", target="it"):
    tradotti = []
    for i, post in enumerate(posts):
        print(f"  Traduzione {i + 1}/{len(posts)}...", end="\r")
        testo_tradotto = traduci(post["testo"], sorgente, target)
        tradotti.append({**post, "testo_tradotto": testo_tradotto})
        time.sleep(0.3)  # pausa breve per evitare rate limiting
    print()
    return tradotti
