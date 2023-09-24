FROM python:3.10-alpine
RUN apk add build-base

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt 
COPY ./main.py ./

EXPOSE 5950
CMD ["python3","-u", "main.py"]
