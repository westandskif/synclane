ARG PY_VERSION="3.9"
FROM python:$PY_VERSION
ARG PY_VERSION="3.9"

ENV USER_NAME=suser
ENV USER_HOME="/home/${USER_NAME}"
ENV PROJ="${USER_HOME}/int_tst"

RUN useradd -ms /bin/bash "${USER_NAME}"
RUN pip install -U pip


COPY requirements$PY_VERSION.out "${USER_HOME}/"
RUN pip install -r "${USER_HOME}/requirements$PY_VERSION.out"

RUN mkdir -p "${PROJ}"
USER suser
WORKDIR "${PROJ}"

EXPOSE 8000

CMD bash -c "pip install -e /mnt/synclane && uvicorn --host=0.0.0.0 --port=8000 main:app"
