ARG PY_VERSION="3.7"
FROM python:$PY_VERSION
ARG PY_VERSION="3.7"

RUN mkdir -p /mnt/synclane
WORKDIR /mnt/synclane

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash \
    && export NVM_DIR="$HOME/.nvm" \
    && \. "$NVM_DIR/nvm.sh" \
    && nvm install node \
    && npm install -D typescript@~5.3 \
    && echo 'export PATH="$PATH:/mnt/synclane/node_modules/.bin"' >> ~/.bashrc

RUN pip install -U pip

COPY requirements$PY_VERSION.out /mnt/synclane/
RUN pip install -r "/mnt/synclane/requirements$PY_VERSION.out"
