FROM python:3-alpine

# install requirements file
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# copy the rest of the files
COPY ./app /app
WORKDIR /app

# run the app
ENTRYPOINT ["python", "app.py"]
