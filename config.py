# ============================================================
#  CONFIGURAZIONE
# ============================================================
import os

# Canale Telegram (pagina web pubblica, nessun account richiesto)
TELEGRAM_URL = "https://t.me/s/evropar"

# Quanti post recenti includere nel podcast
MAX_POST = 15

# Voce italiana per il podcast
# Opzioni: "it-IT-ElsaNeural" (donna), "it-IT-DiegoNeural" (uomo), "it-IT-IsabellaNeural" (donna)
VOCE = "it-IT-ElsaNeural"

# Velocità della voce (0% = normale, +10% = leggermente più veloce)
VELOCITA = "+5%"

# Cartella di output (sincronizzata con OneDrive → telefono)
OUTPUT_DIR = r"G:\Il mio Drive\Notizie Podcast"

# Lingua sorgente (auto = rileva automaticamente)
LINGUA_SORGENTE = "auto"
LINGUA_TARGET = "it"
