FROM python:3.8
COPY requirements.txt requirements.txt
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]