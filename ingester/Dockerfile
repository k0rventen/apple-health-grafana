FROM python:3.11-alpine

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY *.py .
ENTRYPOINT python3 -u app.py