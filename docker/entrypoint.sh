#!/usr/bin/env bash
set -e
set -x

VENV=/.env
VBIN=${VENV}/bin
PIP=${VBIN}/pip
PY=${VBIN}/python3.8

SRC=/bot

if [ "${1:0:1}" = '' ]; then
    set -- run "$@"
fi

virtualenv -p python3.8 ${VENV}
${PIP} install --no-cache-dir -r /requirements.txt

source ${VBIN}/activate

case "$1" in
    run)
        exec ${PY} /bot.py
        exit
        ;;
esac

exec "$@"
