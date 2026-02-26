@echo off
REM ============================================================
REM  WW2 Survival - Test local Serveur + Client
REM ============================================================
cd /d "%~dp0"

REM Chercher python (python ou py)
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYTHON=python
) else (
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PYTHON=py
    ) else (
        echo ERREUR : Python introuvable dans le PATH.
        echo Installez Python ou ajoutez-le au PATH.
        pause
        exit /b 1
    )
)

echo Python trouve : %PYTHON%
echo.
echo Lancement du SERVEUR (fenetre 1)...
start "WW2 - SERVEUR" cmd /k "%PYTHON% main_server.py"

echo Attente 3 secondes avant de lancer le client...
timeout /t 3 /nobreak >nul

echo Lancement du CLIENT (fenetre 2)...
start "WW2 - CLIENT" cmd /k "%PYTHON% main_client.py"

echo.
echo ============================================================
echo  Les deux fenetres sont ouvertes !
echo.
echo  SERVEUR : choisissez votre nom puis HEBERGER
echo  CLIENT  : choisissez votre nom, IP = 127.0.0.1 puis REJOINDRE
echo ============================================================
pause
