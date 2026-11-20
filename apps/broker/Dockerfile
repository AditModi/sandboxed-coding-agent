# Everything the broker trusts is in this image: its code, its rules (broker-policy.json)
# and the CA bundle it uses to check api.github.com. All of it ends up in the image digest,
# which the Cedar policy pins, which the sandbox measures into PCR17, which KMS checks.
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY attested_recipient.py rules.py github.py app.py broker-policy.json /app/
USER 65534:65534
ENTRYPOINT ["python", "/app/app.py"]
