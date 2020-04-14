FROM python:3.8.2-buster

ADD . /app
WORKDIR /app

CMD [ "python", "rssmerger.py" ]