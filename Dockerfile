FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/pricetracker

# Copy only relevant files
COPY pyproject.toml .
COPY pricetracker pricetracker

# Install pricetracker and dependancies
RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    pip install .

# Initialize DB using entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Run server as non-root user
RUN adduser -D myuser
# Note: still using SQLite
RUN mkdir -p /opt/pricetracker/instance && chown -R myuser:myuser /opt/pricetracker/instance
USER myuser


CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "pricetracker:create_app()"]

