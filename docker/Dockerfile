FROM python:3.8.1-buster

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
        apt-utils

RUN apt-get install -y \
        locales

RUN locale-gen ru_RU.UTF-8
RUN locale-gen en_US.UTF-8

RUN pip install --no-cache-dir virtualenv
RUN mkdir /.env
RUN chmod a+rwx /.env

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod a+x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["run"]
