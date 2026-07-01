FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# copy project
COPY . .

# move to src (چون manage.py داخل src هست)
WORKDIR /app/src

# collect static (اگر فعال کردی)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# run server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]