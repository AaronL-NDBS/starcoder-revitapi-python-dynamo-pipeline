@echo off
title StarCoder Revit Pipeline
cd /d "%~dp0"
powershell -NoExit -ExecutionPolicy RemoteSigned -Command "& { .\.venv\Scripts\Activate.ps1; Write-Host 'Virtual environment activated.' -ForegroundColor Green; Write-Host 'Project: starcoder-revitapi-python-dynamo-pipeline' -ForegroundColor Cyan }"
