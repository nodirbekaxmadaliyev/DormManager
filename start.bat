@echo off
cd /d D:\DormManager
call .venv\Scripts\activate.bat
start "" /B pythonw manage.py runserver 0.0.0.0:8000