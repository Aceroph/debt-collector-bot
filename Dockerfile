FROM python:3

WORKDIR /usr/src/app

COPY src/ src/
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "src/main.py" ]
