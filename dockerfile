FROM python:3.14.3
RUN mkdir /code
WORKDIR /code
COPY ./code .
RUN pip3 install -r requirements.txt --no-cache-dir
CMD python bot.py