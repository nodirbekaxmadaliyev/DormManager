@echo off
cd /d D:\DormManager
call venv\Scripts\activate
py manage.py runserver 0.0.0.0:8000
