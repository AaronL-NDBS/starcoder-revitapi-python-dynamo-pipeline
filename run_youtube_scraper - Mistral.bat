@echo off
title YouTube Transcript Scraper
:: Stay in the root directory where the .bat file and .venv live
cd /d "%~dp0"

:: Activate the virtual environment
call .\.venv\Scripts\activate.bat

echo YouTube Scraper ready.
echo Starting...

:: Run the script from the tools folder
python scrapers/youtube_scraper-Mistral.py

pause