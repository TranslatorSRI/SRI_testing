FROM python:3.9
ENV RUNNING_INSIDE_DOCKER True
RUN python -m pip install --upgrade pip
WORKDIR /code
COPY ./requirements*.txt /code
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements-service.txt
COPY ./translator /code/translator
COPY ./tests /code/tests
COPY ./app /code/app
EXPOSE 80
CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]
