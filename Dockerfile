FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt stopwords
COPY . .
EXPOSE 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]