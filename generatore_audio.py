import asyncio
import re

import edge_tts


def pulisci_per_tts(testo):
    testo = re.sub(r"https?://\S+", "", testo)
    testo = re.sub(r"[^\x00-\x7FÀ-ɏЀ-ӿ]", "", testo)
    testo = re.sub(r"\n{3,}", "\n\n", testo)
    testo = re.sub(r" {2,}", " ", testo)
    return testo.strip()


def costruisci_script(posts_tradotti, data_str):
    parti = []
    n = len(posts_tradotti)
    parti.append(
        f"Podcast notizie del {data_str}. "
        f"Canale Europea. {n} notizie di oggi."
    )
    for i, post in enumerate(posts_tradotti, 1):
        testo = post.get("testo_tradotto") or post["testo"]
        testo = pulisci_per_tts(testo)
        if not testo:
            continue
        data_post = post.get("data", "")
        intestazione = f"Notizia {i}"
        if data_post:
            intestazione += f", del {data_post}"
        parti.append(f"{intestazione}. {testo}")
    parti.append("Fine del podcast. Buona giornata.")
    return "\n\n".join(parti)


async def _genera_async(testo, output_path, voce, velocita):
    communicate = edge_tts.Communicate(testo, voce, rate=velocita)
    sentence_boundaries = []
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                sentence_boundaries.append({
                    "text": chunk["text"],
                    "offset_s": round(chunk["offset"] / 10_000_000, 2),
                })
    return sentence_boundaries


def _trova_tempi_articoli(sentence_boundaries, num_articoli):
    """Ricava il tempo di inizio (in secondi) di ogni articolo dal boundary 'Notizia N.'."""
    tempi = {}
    for sb in sentence_boundaries:
        m = re.match(r"^Notizia\s+(\d+)", sb["text"])
        if m:
            num = int(m.group(1))
            if 1 <= num <= num_articoli and num not in tempi:
                tempi[num] = sb["offset_s"]
    return tempi


def genera_audio(testo, output_path, voce, velocita, num_articoli=0):
    """
    Genera l'audio MP3 e restituisce un dizionario {numero_articolo: secondi_inizio}.
    Se num_articoli=0 restituisce un dizionario vuoto.
    """
    sentence_boundaries = asyncio.run(
        _genera_async(testo, output_path, voce, velocita)
    )
    if num_articoli > 0:
        return _trova_tempi_articoli(sentence_boundaries, num_articoli)
    return {}
