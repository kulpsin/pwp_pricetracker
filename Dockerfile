FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/pricetracker

RUN apk add --no-cache su-exec

# Copy only relevant files
COPY pyproject.toml .
COPY pricetracker pricetracker

# Install pricetracker and dependencies
RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    pip install .

# Setup the entrypoint i.e. for DB init
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

RUN adduser -D myuser
ENV FLASK_APP=pricetracker

CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "pricetracker:create_app()"]
