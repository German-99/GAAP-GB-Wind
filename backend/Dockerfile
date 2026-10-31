FROM python:3.12-slim
 
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
 
WORKDIR /app
 
# Install dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# The application code and the Elexon snapshot (data/raw/*.parquet).
COPY app ./app
COPY data ./data
 
# Do not run as root.
RUN useradd --create-home appuser
USER appuser
 
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]