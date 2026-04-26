FROM python:3.8.5
RUN  apt install nano
RUN mkdir /code
WORKDIR /code
COPY ./code .
RUN pip3 install -r requirements.txt --no-cache-dir
CMD python bot.py