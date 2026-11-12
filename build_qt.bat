@echo off
cd /d %~dp0
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name "AI-oka_passwd 0.01" --icon "assets\logo_color.ico" --add-data "assets;assets" app\qt_app.py
