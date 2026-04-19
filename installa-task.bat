@echo off
echo Installo task automatico...

set SCRIPT=C:\Users\Andrea Della Corte\notizie-podcast\main.py

:: Task giornaliero alle 7:00
schtasks /create /tn "NotiziePodcast" /tr "python \"%SCRIPT%\"" /sc daily /st 07:00 /f /rl HIGHEST

:: Aggiunge anche l'opzione "esegui se perso" (utile se il PC era spento alle 7)
schtasks /change /tn "NotiziePodcast" /rl HIGHEST

if errorlevel 1 (
    echo.
    echo ERRORE: esegui questo file come Amministratore.
    echo Tasto destro sul file - Esegui come amministratore
    pause
    exit /b 1
)

echo.
echo Task installato! Il podcast si genera ogni giorno alle 7:00.
echo Se il PC era spento alle 7:00, si genera appena lo accendi.
pause
