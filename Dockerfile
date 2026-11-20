FROM python:3.12-slim
WORKDIR /app
COPY demo_service.py .
ENV PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8080
CMD ["python", "demo_service.py"]
