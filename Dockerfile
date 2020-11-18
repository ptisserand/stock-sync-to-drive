FROM tiangolo/uwsgi-nginx-flask:python3.8
LABEL maintainer="p.tisserand@gmail.com"

WORKDIR /app/
COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY ./uwsgi.ini /app
COPY ./stock_syncer.py /app
COPY ./web /app/web
ENV STATIC_PATH /app/web/static

EXPOSE 80
