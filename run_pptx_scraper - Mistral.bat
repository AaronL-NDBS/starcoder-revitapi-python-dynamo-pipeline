@echo off
title PowerPoint Scraper
:: Ensure we are in the directory where the .bat file lives
cd /d "%~dp0"

:: Activate the virtual environment
call .\.venv\Scripts\activate.bat

:: Run the script using a relative path
python scrapers/pptx_scraper-Mistral.py

pause