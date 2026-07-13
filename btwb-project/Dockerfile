FROM python:3.13-slim

WORKDIR /app

COPY btwb-project/requirements.txt .
RUN pip install -r requirements.txt

COPY btwb-project/ .

EXPOSE $PORT

CMD ["python", "app.py"]
