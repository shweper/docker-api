FROM python:3.12.5-alpine3.19

WORKDIR /usr/src/app
COPY . .
EXPOSE 8000
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "uvicorn[standard]"
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]