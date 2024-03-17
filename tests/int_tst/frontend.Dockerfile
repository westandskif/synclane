FROM node:lts

RUN useradd -ms /bin/bash suser

RUN mkdir -p /home/suser/int_tst
COPY package.json package-lock.json /home/suser/int_tst
RUN chown -R suser:suser /home/suser/int_tst

ENV TZ=America/New_York

USER suser
WORKDIR /home/suser/int_tst
RUN npm install

CMD npm test
