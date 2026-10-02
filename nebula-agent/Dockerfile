FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends docker.io ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY agent.py /app/agent.py
CMD ["python","agent.py"]
