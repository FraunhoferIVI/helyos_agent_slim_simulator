FROM python:3.8-slim-buster

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
# RUN python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple helyos-agent-sdk==0.7.4-rc1
COPY src/ .


CMD [ "python", "-u" , "main.py"]