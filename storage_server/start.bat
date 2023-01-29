@echo off
if not exist venv\ (
echo "venv not found creating new one..."
python -m venv venv
call venv\Scripts\pip.exe install -r requirements.txt
)
call venv\Scripts\python.exe main.py