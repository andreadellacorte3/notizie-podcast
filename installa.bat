@echo off
echo ============================================
echo   SETUP NOTIZIE PODCAST
echo ============================================
echo.
cd /d "%~dp0"

echo Controllo Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato.
    echo Scaricalo da https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

echo Installo dipendenze...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRORE durante l'installazione delle dipendenze.
    pause
    exit /b 1
)

echo.
echo Test di funzionamento...
python main.py

echo.
echo ============================================
echo Installazione completata!
echo Ora esegui "installa-task.bat" come
echo amministratore per il refresh automatico.
echo ============================================
pause
