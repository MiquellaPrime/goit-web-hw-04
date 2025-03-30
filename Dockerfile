FROM python:3.11-slim

ENV APP_HOME=/app

WORKDIR $APP_HOME

COPY . .

ENTRYPOINT ["python", "main.py"]