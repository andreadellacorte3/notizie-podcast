import asyncio
import edge_tts
import re


def pulisci_per_tts(testo):
    """Rimuove elementi che suonano male nel text-to-speech."""
    # Rimuovi URL
    testo = re.sub(r"https?://\S+", "", testo)
    # Rimuovi emoji (caratteri non ASCII estesi)
    testo = re.sub(r"[^\x00-\x7F\u00C0-\u024F\u0400-\u04FF]", "", testo)
    # Rimuovi righe vuote multiple
    testo = re.sub(r"\n{3,}", "\n\n", testo)
    # Normalizza spazi
    testo = re.sub(r" {2,}", " ", testo)
    return testo.strip()


def costruisci_script(posts_tradotti, data_str):
    """Costruisce il testo completo del podcast."""
    parti = []

    # Intro
    n = len(posts_tradotti)
    parti.append(
        f"Podcast notizie del {data_str}. "
        f"Canale Europea. {n} notizie di oggi."
    )

    # Ogni notizia
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

    # Outro
    parti.append("Fine del podcast. Buona giornata.")

    return "\n\n".join(parti)


async def _genera_audio_async(testo, output_path, voce, velocita):
    communicate = edge_tts.Communicate(testo, voce, rate=velocita)
    await communicate.save(output_path)


def genera_audio(testo, output_path, voce, velocita):
    asyncio.run(_genera_audio_async(testo, output_path, voce, velocita))
