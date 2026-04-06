FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/pricetracker

RUN apk add --no-cache git

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser -D myuser
USER myuser

CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "pricetracker:create_app()"]