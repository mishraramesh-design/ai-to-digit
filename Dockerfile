FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN mkdir -p /data/runs && chown -R 10001:10001 /data
COPY digit_harness/ digit_harness/
USER 10001:10001
EXPOSE 8090
CMD ["python", "-m", "digit_harness.server", "--bind", "0.0.0.0", "--data", "/data/runs"]
