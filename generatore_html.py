import json


def genera_html(posts_tradotti, data_str, nome_audio, tempi_articoli=None):
    """
    Genera la pagina HTML con:
    - Player audio con pulsanti ±10 secondi
    - Click su un articolo per saltare a quel punto dell'audio
    - Tracciamento progresso: ripresa dal punto lasciato (localStorage)
    - Indicatori visivi di articoli ascoltati / in corso / da ascoltare
    """
    if tempi_articoli is None:
        tempi_articoli = {}

    tempi_js = json.dumps({str(k): v for k, v in tempi_articoli.items()})
    ha_timing = "true" if tempi_articoli else "false"

    def _rimuovi_tag(testo):
        import re as _re
        righe = testo.split("\n")
        pulite = [r for r in righe if not (r.strip().split() and all(
            p.startswith("#") or p.startswith("@") for p in r.strip().split()))]
        testo = "\n".join(pulite)
        return _re.sub(r"\s+([@#]\S+\s*)+$", "", testo).strip()

    notizie_html = ""
    for i, post in enumerate(posts_tradotti, 1):
        testo = _rimuovi_tag(post.get("testo_tradotto") or post["testo"])
        data_post = post.get("data", "")
        testo_html = testo.replace("\n", "<br>")
        clic_attr = f' onclick="seekToArticle({i})" title="Tocca per ascoltare"' if i in tempi_articoli else ""

        notizie_html += f"""
    <article id="art-{i}" data-num="{i}"{clic_attr}>
        <div class="num">#{i}{f' <span class="data-post">{data_post}</span>' if data_post else ''}</div>
        <p>{testo_html}</p>
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

/* Banner ripresa */
#banner-ripresa{{display:none;background:#1e3a5f;border:1px solid #2d5a8e;border-radius:10px;padding:12px 16px;margin-bottom:16px;cursor:pointer;font-size:.9rem;color:#7ec8f0}}
#banner-ripresa:active{{background:#173050}}

/* Player */
.player{{background:#1a1a1a;border-radius:12px;padding:16px;margin-bottom:24px}}
.player-label{{font-size:.82rem;color:#888;margin-bottom:10px}}
audio{{width:100%;border-radius:8px;margin-bottom:12px}}
.skip-row{{display:flex;gap:10px;justify-content:center}}
.skip-btn{{flex:1;max-width:160px;background:#252525;border:1px solid #333;border-radius:8px;color:#ccc;font-size:.9rem;padding:9px 0;cursor:pointer;transition:background .15s}}
.skip-btn:active{{background:#333}}
.prima-notizia-btn{{width:100%;background:#1a2a1a;border:1px solid #2d4a2d;border-radius:8px;color:#7fcf7f;font-size:.85rem;padding:9px 0;cursor:pointer;margin-top:10px;display:none}}
.prima-notizia-btn:active{{background:#213021}}

/* Articoli */
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

<div id="banner-ripresa" onclick="riprendi()">
  ▶ Riprendi dall'ultimo punto ascoltato
</div>

<div class="player">
  <div class="player-label">Ascolta (funziona in background con schermo spento)</div>
  <audio id="player" controls>
    <source src="{nome_audio}" type="audio/mpeg">
    Audio non supportato.
  </audio>
  <div class="skip-row">
    <button class="skip-btn" onclick="salta(-10)">⏪ −10 sec</button>
    <button class="skip-btn" onclick="salta(+10)">+10 sec ⏩</button>
  </div>
  <button id="btn-prima-notizia" class="prima-notizia-btn" onclick="sallaAllaProximaNotizia()">
    ⬇ Vai alla prima notizia non ascoltata
  </button>
</div>

{notizie_html}

<footer>Generato automaticamente · {len(posts_tradotti)} notizie</footer>

<script>
const TIMES = {tempi_js};
const HA_TIMING = {ha_timing};
const audio = document.getElementById('player');
const storageKey = 'podcast_pos::' + location.pathname;
let savedPos = parseFloat(localStorage.getItem(storageKey) || '0');

/* ── Ripresa posizione ─────────────────────────────────── */
if (savedPos > 5) {{
  document.getElementById('banner-ripresa').style.display = 'block';
  document.getElementById('banner-ripresa').textContent =
    '▶ Riprendi dall\\'ultimo punto (' + formatTime(savedPos) + ')';
}}

function riprendi() {{
  audio.currentTime = savedPos;
  audio.play();
  document.getElementById('banner-ripresa').style.display = 'none';
}}

/* ── Skip ±10 secondi ──────────────────────────────────── */
function salta(delta) {{
  audio.currentTime = Math.max(0, audio.currentTime + delta);
}}

/* ── Seek sull'articolo ────────────────────────────────── */
function seekToArticle(num) {{
  const t = TIMES[String(num)];
  if (t !== undefined) {{
    audio.currentTime = t;
    audio.play();
  }}
}}

/* ── Aggiornamento indicatori in tempo reale ───────────── */
audio.addEventListener('timeupdate', () => {{
  const t = audio.currentTime;
  localStorage.setItem(storageKey, t);

  if (!HA_TIMING) return;

  const nums = Object.keys(TIMES).map(Number).sort((a, b) => a - b);
  let prossimaNum = null;

  nums.forEach((num, idx) => {{
    const start = TIMES[String(num)];
    const end = TIMES[String(nums[idx + 1])] ?? Infinity;
    const el = document.getElementById('art-' + num);
    if (!el) return;

    const badgeEl = el.querySelector('.badge-stato');

    if (t >= start && t < end) {{
      // articolo corrente
      el.classList.add('in-corso');
      el.classList.remove('ascoltato', 'prossima');
      if (!badgeEl) {{
        const b = document.createElement('span');
        b.className = 'badge-stato badge-inCorso';
        b.textContent = '▶ in ascolto';
        el.querySelector('.num').appendChild(b);
      }}
    }} else if (t >= end) {{
      // già ascoltato
      el.classList.add('ascoltato');
      el.classList.remove('in-corso', 'prossima');
      if (badgeEl) badgeEl.remove();
    }} else {{
      // non ancora ascoltato
      el.classList.remove('in-corso', 'ascoltato');
      if (badgeEl) badgeEl.remove();
      if (prossimaNum === null) prossimaNum = num;
    }}
  }});

  // Evidenzia la prima notizia non ascoltata
  nums.forEach(num => {{
    const el = document.getElementById('art-' + num);
    if (!el) return;
    if (num === prossimaNum) {{
      el.classList.add('prossima');
      const b = el.querySelector('.badge-stato');
      if (!b) {{
        const nb = document.createElement('span');
        nb.className = 'badge-stato badge-prossima';
        nb.textContent = '● prossima';
        el.querySelector('.num').appendChild(nb);
      }}
    }} else {{
      el.classList.remove('prossima');
    }}
  }});

  // Mostra/nasconde il pulsante "Vai alla prima notizia non ascoltata"
  const btn = document.getElementById('btn-prima-notizia');
  btn.style.display = (prossimaNum !== null && t > 2) ? 'block' : 'none';
}});

function sallaAllaProximaNotizia() {{
  const t = audio.currentTime;
  const nums = Object.keys(TIMES).map(Number).sort((a, b) => a - b);
  for (const num of nums) {{
    if (TIMES[String(num)] > t + 1) {{
      seekToArticle(num);
      document.getElementById('art-' + num).scrollIntoView({{behavior: 'smooth', block: 'start'}});
      return;
    }}
  }}
}}

/* ── Utilità ───────────────────────────────────────────── */
function formatTime(s) {{
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, '0');
  return m + ':' + ss;
}}

/* Segna gli articoli seekable */
if (HA_TIMING) {{
  Object.keys(TIMES).forEach(num => {{
    const el = document.getElementById('art-' + num);
    if (el) el.classList.add('seekable');
  }});
}}
</script>
</body>
</html>"""
