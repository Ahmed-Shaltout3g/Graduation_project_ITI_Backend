# Use an official Python runtime as a parent image
FROM python:3.10-slim-bullseye

WORKDIR /app

# Install psycopg2 dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc

# Copy requirements first
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the project including media
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
