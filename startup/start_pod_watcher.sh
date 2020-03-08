#! /usr/bin/env bash

function usage() {
    echo "usage: start.sh <setup.env file>"
}

function err() {
    msg=$1
    echo "$1" 1>&2
    exit 1
}

if [ $# -ne 1 ]
then
    usage && exit 1
fi

echo ""
echo "$(date) ==== Start Aves2 Server ===="


ENV_FILE=$1
GUNICORN_CFG=$2

[ -f ${ENV_FILE} ] || err "${ENV_FILE} is not exist"
[ -f ${GUNICORN_CFG} ] || err "${GUNICORN_CFG} is not exist"
source ${ENV_FILE}

[ ! -z ${DJANGO_PROJ_PATH} ] || err "${DJANGO_PROJ_PATH} is not defined"
cd ${DJANGO_PROJ_PATH}
exec python3 manage.py watch_pod
