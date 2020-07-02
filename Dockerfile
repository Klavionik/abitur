FROM python:3.8
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DJANGO_SETTINGS_MODULE 'snailchen.settings'
RUN mkdir /var/app
WORKDIR /var/app
RUN apt-get update && apt-get install ghostscript -y
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /var/app
CMD ["uwsgi", "uwsgi.ini"]