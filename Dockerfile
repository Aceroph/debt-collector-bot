FROM python:3

WORKDIR /usr/src/app

RUN git clone https://github.com/Aceroph/debt-collector-bot.git .
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "main.py" ]
