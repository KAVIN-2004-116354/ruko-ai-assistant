FROM python:3.10-slim
WORKDIR /app
COPY email_agent.py .
RUN pip install requests ollama
CMD ["python3", "-u", "email_agent.py"]
