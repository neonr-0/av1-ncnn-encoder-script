#!/bin/bash
if [ ! -d venv ]
then
    echo "venv not found creating new one..."
    python3 -m venv venv
    exec venv/bin/pip install -r requirements.txt
fi
exec venv/bin/python3 main.py