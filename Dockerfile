FROM python:3.12-slim
WORKDIR /app
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    sed -i 's/Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core ttf-mscorefonts-installer && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8777
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8777"]
