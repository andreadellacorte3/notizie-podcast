from datetime import datetime


def genera_html(posts_tradotti, data_str, nome_audio):
    """
    Genera una pagina HTML leggibile su telefono con le notizie tradotte.
    Include un player audio integrato.
    """
    notizie_html = ""
    for i, post in enumerate(posts_tradotti, 1):
        testo = post.get("testo_tradotto") or post["testo"]
        data_post = post.get("data", "")
        testo_html = testo.replace("\n", "<br>")

        notizie_html += f"""
        <article>
            <div class="numero">#{i}</div>
            {"<div class='data'>" + data_post + "</div>" if data_post else ""}
            <p>{testo_html}</p>
        </article>
        """

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notizie {data_str}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #e8e8e8;
            padding: 16px;
            max-width: 700px;
            margin: 0 auto;
        }}
        header {{
            padding: 20px 0 16px;
            border-bottom: 1px solid #333;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 1.1rem;
            color: #aaa;
            font-weight: 400;
        }}
        h2 {{
            font-size: 1.5rem;
            color: #fff;
            margin-top: 4px;
        }}
        .player-box {{
            background: #1a1a1a;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
        }}
        .player-box p {{
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 10px;
        }}
        audio {{
            width: 100%;
            border-radius: 8px;
        }}
        article {{
            background: #1a1a1a;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        .numero {{
            font-size: 0.75rem;
            color: #555;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        .data {{
            font-size: 0.78rem;
            color: #666;
            margin-bottom: 10px;
        }}
        article p {{
            font-size: 0.95rem;
            line-height: 1.65;
            color: #ddd;
        }}
        footer {{
            text-align: center;
            color: #444;
            font-size: 0.75rem;
            padding: 30px 0 16px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Canale Europea — traduzione automatica</h1>
        <h2>{data_str}</h2>
    </header>

    <div class="player-box">
        <p>Ascolta il podcast (funziona in background)</p>
        <audio controls>
            <source src="{nome_audio}" type="audio/mpeg">
            Audio non supportato.
        </audio>
    </div>

    {notizie_html}

    <footer>Generato automaticamente · {len(posts_tradotti)} notizie</footer>
</body>
</html>"""
