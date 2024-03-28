FROM python:3.10.11

WORKDIR /app

COPY requirements.txt ./

COPY app.py ./

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
