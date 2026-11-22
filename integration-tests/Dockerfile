# Tests of the integration in custom_components/: Home Assistant's Python and its test helpers.
FROM python:3.14.9-slim-trixie

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt /tmp/requirements.txt
RUN pip install --require-hashes -r /tmp/requirements.txt
WORKDIR /work
