# The brain. It holds no secret: its Pod Identity role can call Bedrock and nothing else,
# and its Kubernetes RBAC reaches the agent-hands namespace and nothing else.
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY agent.py workspace.py /app/
COPY experiments/ /app/experiments/
USER 65534:65534
ENTRYPOINT ["python", "/app/agent.py"]
