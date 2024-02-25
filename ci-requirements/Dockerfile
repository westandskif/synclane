ARG PY_VERSION="3.6"
FROM python:$PY_VERSION
ARG PY_VERSION="3.6"

RUN pip install -U pip

RUN mkdir -p /mnt/synclane
COPY requirements$PY_VERSION.out /mnt/synclane/
RUN pip install -r "/mnt/synclane/requirements$PY_VERSION.out"

WORKDIR /mnt/synclane
