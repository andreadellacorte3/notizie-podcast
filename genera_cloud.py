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
VOCE = "it-IT-ElsaNeural"   # usata solo se Cartesia non è configurata
VELOCITA = "+5%"
OUTPUT_DIR = "docs"
CARTESIA_API_KEY  = os.environ.get("CARTESIA_API_KEY", "")
CARTESIA_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "")
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
        for br in el.find_all("br"):
            br.replace_with(" ")
        testo = el.get_text(separator=" ").strip()
        testo = re.sub(r"[»«]", "", testo)
        testo = re.sub(r" {2,}", " ", testo)
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


EMAIL = "andreadellacorte3@gmail.com"  # aumenta quota MyMemory a 50k parole/giorno


def _ha_cirillico(testo):
    cirillici = sum(1 for c in testo if 'Ѐ' <= c <= 'ӿ')
    return cirillici > len(testo) * 0.15


def _mymemory(blocco, retries=4):
    """MyMemory con email: 50k parole/giorno, blocchi max 490 caratteri."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": blocco, "langpair": "ru|it", "de": EMAIL},
                headers=HEADERS,
                timeout=15,
            )
            data = resp.json()
            if data.get("responseStatus") == 200:
                t = data["responseData"]["translatedText"]
                if t and t.strip() and not _ha_cirillico(t):
                    return t
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
    return None


def _google(testo, retries=2):
    """Google Translate come backup (può essere bloccato da alcuni ambienti CI)."""
    url = "https://translate.googleapis.com/translate_a/single"
    data = {"client": "gtx", "sl": "auto", "tl": "it", "dt": "t", "q": testo}
    for attempt in range(retries):
        try:
            resp = requests.post(url, data=data, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            t = "".join(part[0] for part in result[0] if part[0])
            if t.strip() and not _ha_cirillico(t):
                return t
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(2)
    return None


def _spezza_in_blocchi(testo, limite=480):
    """Spezza per MyMemory (limite 500 chars), preserva le frasi."""
    frasi = re.split(r'(?<=[.!?])\s+', testo)
    blocchi, corrente = [], ""
    for frase in frasi:
        if len(corrente) + len(frase) + 1 <= limite:
            corrente += (" " if corrente else "") + frase
        else:
            if corrente:
                blocchi.append(corrente)
            while len(frase) > limite:
                blocchi.append(frase[:limite])
                frase = frase[limite:]
            corrente = frase
    if corrente:
        blocchi.append(corrente)
    return blocchi


def _spezza_grande(testo, limite=4500):
    """Spezza per Google Translate (limite ~4500 chars), per paragrafi."""
    if len(testo) <= limite:
        return [testo]
    paragrafi = testo.split("\n")
    blocchi, corrente = [], ""
    for p in paragrafi:
        if len(corrente) + len(p) + 1 <= limite:
            corrente += p + "\n"
        else:
            if corrente.strip():
                blocchi.append(corrente.strip())
            corrente = p + "\n"
    if corrente.strip():
        blocchi.append(corrente.strip())
    return blocchi


def traduci(testo):
    testo = rimuovi_emoji(testo)
    if not testo.strip():
        return testo

    # 1. Google prima: blocchi grandi (più contesto = traduzione migliore)
    blocchi_grandi = _spezza_grande(testo)
    risultati = []
    google_ok = True
    for i, b in enumerate(blocchi_grandi):
        t = _google(b)
        if t is None or _ha_cirillico(t):
            google_ok = False
            break
        risultati.append(t)
        if i < len(blocchi_grandi) - 1:
            time.sleep(0.3)

    if google_ok:
        return "\n".join(risultati)

    # 2. Fallback MyMemory: blocchi piccoli (qualità inferiore ma più affidabile in CI)
    blocchi = _spezza_in_blocchi(testo)
    risultati = []
    for i, b in enumerate(blocchi):
        t = _mymemory(b) or _google(b) or b
        risultati.append(t)
        if i < len(blocchi) - 1:
            time.sleep(0.5)
    return "\n".join(risultati)


def traduci_lista(posts):
    risultato = []
    for i, post in enumerate(posts):
        log(f"  Traduzione {i + 1}/{len(posts)}...")
        tradotto = traduci(post["testo"])
        risultato.append({**post, "testo_tradotto": tradotto})
        time.sleep(0.5)
    return risultato


# ── Audio ───────────────────────────────────────────────────

def rimuovi_tag(testo):
    """Rimuove righe di soli #hashtag/@menzioni e tag in coda al testo."""
    righe = testo.split("\n")
    pulite = []
    for riga in righe:
        parole = riga.strip().split()
        if parole and all(p.startswith("#") or p.startswith("@") for p in parole):
            continue
        pulite.append(riga)
    testo = "\n".join(pulite)
    # rimuovi anche tag/menzioni in coda sulla stessa riga
    testo = re.sub(r"\s+([@#]\S+\s*)+$", "", testo)
    return testo.strip()


def pulisci_tts(testo):
    testo = rimuovi_emoji(testo)
    testo = rimuovi_tag(testo)
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


async def _edge_tts_stream(testo, path, voce, velocita):
    communicate = edge_tts.Communicate(testo, voce, rate=velocita)
    sentence_boundaries = []
    with open(path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                sentence_boundaries.append({
                    "text": chunk["text"],
                    "offset_s": round(chunk["offset"] / 10_000_000, 2),
                })
    return sentence_boundaries


def _trova_tempi(sentence_boundaries, num_articoli):
    tempi = {}
    for sb in sentence_boundaries:
        m = re.match(r"^Notizia\s+(\d+)", sb["text"])
        if m:
            num = int(m.group(1))
            if 1 <= num <= num_articoli and num not in tempi:
                tempi[num] = sb["offset_s"]
    return tempi


def _spezza_script(testo, limite=7000):
    """Spezza il testo per articolo mantenendo ogni blocco sotto il limite di caratteri."""
    if len(testo) <= limite:
        return [testo]
    paragrafi = testo.split("\n\n")
    chunks, corrente = [], ""
    for p in paragrafi:
        if len(corrente) + len(p) + 2 <= limite:
            corrente += p + "\n\n"
        else:
            if corrente.strip():
                chunks.append(corrente.strip())
            corrente = p + "\n\n"
    if corrente.strip():
        chunks.append(corrente.strip())
    return chunks


def _cartesia_chunk(testo):
    """Chiama Cartesia /tts/bytes e restituisce (audio_bytes, [])."""
    resp = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "X-API-Key": CARTESIA_API_KEY,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        },
        json={
            "model_id": "sonic-2",
            "transcript": testo,
            "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
            "output_format": {"container": "mp3", "encoding": "mp3", "sample_rate": 44100},
            "language": "it",
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.content, []


def _cartesia(testo, path, num_articoli):
    """Genera il podcast con Cartesia, gestisce testi lunghi e recupera i timestamp."""
    chunks = _spezza_script(testo)
    tutto_audio = bytearray()
    tutte_parole = []
    offset = 0.0

    for i, chunk in enumerate(chunks):
        log(f"  Cartesia chunk {i+1}/{len(chunks)}...")
        audio, parole = _cartesia_chunk(chunk)
        for w, t in parole:
            tutte_parole.append((w, round(t + offset, 2)))
        # offset successivo = fine ultima parola + margine
        offset += (parole[-1][1] + 1.0) if parole else (len(audio) / 16000.0)
        tutto_audio.extend(audio)
        if i < len(chunks) - 1:
            time.sleep(0.5)

    with open(path, "wb") as f:
        f.write(tutto_audio)

    # Trova i tempi di inizio di ogni articolo ("Notizia N")
    tempi = {}
    for i, (w, t) in enumerate(tutte_parole):
        if w.lower() == "notizia":
            for w2, _ in tutte_parole[i+1:i+3]:
                try:
                    num = int(w2.rstrip(".,"))
                    if 1 <= num <= num_articoli and num not in tempi:
                        tempi[num] = t
                    break
                except ValueError:
                    pass
    return tempi if num_articoli > 0 else {}


def genera_audio(testo, path, num_articoli=0):
    if CARTESIA_API_KEY and CARTESIA_VOICE_ID:
        try:
            log("Uso Cartesia (voce clonata)...")
            return _cartesia(testo, path, num_articoli)
        except requests.exceptions.HTTPError as e:
            log(f"Cartesia non disponibile ({e.response.status_code}), uso edge-tts...")
        except Exception as e:
            log(f"Errore Cartesia ({e}), uso edge-tts...")
    log("Uso edge-tts (voce standard)...")
    sb = asyncio.run(_edge_tts_stream(testo, path, VOCE, VELOCITA))
    return _trova_tempi(sb, num_articoli) if num_articoli > 0 else {}


# ── HTML ────────────────────────────────────────────────────

def genera_html(posts, data_str, nome_audio, tempi_articoli=None):
    import json as _json
    if tempi_articoli is None:
        tempi_articoli = {}

    tempi_js = _json.dumps({str(k): v for k, v in tempi_articoli.items()})
    ha_timing = "true" if tempi_articoli else "false"

    notizie = ""
    for i, p in enumerate(posts, 1):
        testo = rimuovi_tag(p.get("testo_tradotto") or p["testo"]).replace("\n", "<br>")
        data_p = p.get("data", "")
        clic_attr = f' onclick="seekToArticle({i})" title="Tocca per ascoltare"' if i in tempi_articoli else ""
        notizie += f"""
    <article id="art-{i}" data-num="{i}"{clic_attr}>
        <div class="num">#{i}{f' <span class="data-post">{data_p}</span>' if data_p else ''}</div>
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
#banner-ripresa{{display:none;background:#1e3a5f;border:1px solid #2d5a8e;border-radius:10px;padding:12px 16px;margin-bottom:16px;cursor:pointer;font-size:.9rem;color:#7ec8f0}}
#banner-ripresa:active{{background:#173050}}
.player{{background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:24px}}
.player-label{{font-size:.82rem;color:#888;margin-bottom:10px}}
audio{{width:100%;border-radius:8px;margin-bottom:12px}}
.skip-row{{display:flex;gap:10px;justify-content:center}}
.skip-btn{{flex:1;max-width:160px;background:#252525;border:1px solid #333;border-radius:8px;color:#ccc;font-size:.9rem;padding:9px 0;cursor:pointer}}
.skip-btn:active{{background:#333}}
.prima-notizia-btn{{width:100%;background:#1a2a1a;border:1px solid #2d4a2d;border-radius:8px;color:#7fcf7f;font-size:.85rem;padding:9px 0;cursor:pointer;margin-top:10px;display:none}}
article{{background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:14px;border-left:3px solid transparent;transition:border-color .3s,opacity .3s,background .15s}}
article.seekable{{cursor:pointer}}
article.seekable:active{{background:#222}}
article.in-corso{{border-left-color:#4a9eff;background:#141c2a}}
article.ascoltato{{opacity:.45}}
article.prossima{{border-left-color:#4caf50}}
.num{{font-size:.75rem;color:#555;font-weight:600;margin-bottom:8px;display:flex;align-items:center;gap:8px}}
.data-post{{color:#555;font-weight:400}}
.badge-inCorso{{background:#1a3050;color:#4a9eff;font-size:.65rem;padding:2px 6px;border-radius:4px;font-weight:600}}
.badge-prossima{{background:#1a301a;color:#4caf50;font-size:.65rem;padding:2px 6px;border-radius:4px;font-weight:600}}
article p{{font-size:.95rem;line-height:1.65;color:#ddd}}
article.ascoltato p{{color:#888}}
footer{{text-align:center;color:#444;font-size:.75rem;padding:30px 0 16px}}
</style>
</head>
<body>
<header>
  <h1>Canale Europea — traduzione automatica</h1>
  <h2>{data_str}</h2>
</header>
<div id="banner-ripresa" onclick="riprendi()">▶ Riprendi dall'ultimo punto ascoltato</div>
<div class="player">
  <div class="player-label">Ascolta (funziona in background con schermo spento)</div>
  <audio id="player" controls><source src="{nome_audio}" type="audio/mpeg">Audio non supportato.</audio>
  <div class="skip-row">
    <button class="skip-btn" onclick="salta(-10)">⏪ −10 sec</button>
    <button class="skip-btn" onclick="salta(+10)">+10 sec ⏩</button>
  </div>
  <button id="btn-prima-notizia" class="prima-notizia-btn" onclick="sallaAllaProximaNotizia()">⬇ Vai alla prima notizia non ascoltata</button>
</div>
{notizie}
<footer>Aggiornato automaticamente ogni mattina · {len(posts)} notizie</footer>
<script>
const TIMES={tempi_js};
const HA_TIMING={ha_timing};
const audio=document.getElementById('player');
const storageKey='podcast_pos::'+location.pathname;
let savedPos=parseFloat(localStorage.getItem(storageKey)||'0');
if(savedPos>5){{
  const b=document.getElementById('banner-ripresa');
  b.style.display='block';
  b.textContent='▶ Riprendi dall\\'ultimo punto ('+formatTime(savedPos)+')';
}}
function riprendi(){{audio.currentTime=savedPos;audio.play();document.getElementById('banner-ripresa').style.display='none';}}
function salta(d){{audio.currentTime=Math.max(0,audio.currentTime+d);}}
function seekToArticle(n){{const t=TIMES[String(n)];if(t!==undefined){{audio.currentTime=t;audio.play();}}}}
audio.addEventListener('timeupdate',()=>{{
  const t=audio.currentTime;
  localStorage.setItem(storageKey,t);
  if(!HA_TIMING)return;
  const nums=Object.keys(TIMES).map(Number).sort((a,b)=>a-b);
  let prossimaNum=null;
  nums.forEach((num,idx)=>{{
    const start=TIMES[String(num)];
    const end=TIMES[String(nums[idx+1])]??Infinity;
    const el=document.getElementById('art-'+num);
    if(!el)return;
    const badgeEl=el.querySelector('.badge-stato');
    if(t>=start&&t<end){{
      el.classList.add('in-corso');el.classList.remove('ascoltato','prossima');
      if(!badgeEl){{const b=document.createElement('span');b.className='badge-stato badge-inCorso';b.textContent='▶ in ascolto';el.querySelector('.num').appendChild(b);}}
    }}else if(t>=end){{
      el.classList.add('ascoltato');el.classList.remove('in-corso','prossima');
      if(badgeEl)badgeEl.remove();
    }}else{{
      el.classList.remove('in-corso','ascoltato');
      if(badgeEl)badgeEl.remove();
      if(prossimaNum===null)prossimaNum=num;
    }}
  }});
  nums.forEach(num=>{{
    const el=document.getElementById('art-'+num);
    if(!el)return;
    if(num===prossimaNum){{
      el.classList.add('prossima');
      const b=el.querySelector('.badge-stato');
      if(!b){{const nb=document.createElement('span');nb.className='badge-stato badge-prossima';nb.textContent='● prossima';el.querySelector('.num').appendChild(nb);}}
    }}else{{el.classList.remove('prossima');}}
  }});
  document.getElementById('btn-prima-notizia').style.display=(prossimaNum!==null&&t>2)?'block':'none';
}});
function sallaAllaProximaNotizia(){{
  const t=audio.currentTime;
  const nums=Object.keys(TIMES).map(Number).sort((a,b)=>a-b);
  for(const num of nums){{if(TIMES[String(num)]>t+1){{seekToArticle(num);document.getElementById('art-'+num).scrollIntoView({{behavior:'smooth',block:'start'}});return;}}}}
}}
function formatTime(s){{const m=Math.floor(s/60);const ss=Math.floor(s%60).toString().padStart(2,'0');return m+':'+ss;}}
if(HA_TIMING){{Object.keys(TIMES).forEach(num=>{{const el=document.getElementById('art-'+num);if(el)el.classList.add('seekable');}});}}
</script>
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
    tempi_articoli = genera_audio(
        costruisci_script(posts, data_str),
        f"{OUTPUT_DIR}/{nome_audio}",
        len(posts),
    )
    log(f"Audio generato. Timing per {len(tempi_articoli)} articoli.")

    nome_html = f"notizie_{prefisso}.html"
    with open(f"{OUTPUT_DIR}/{nome_html}", "w", encoding="utf-8") as f:
        f.write(genera_html(posts, data_str, nome_audio, tempi_articoli))
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
