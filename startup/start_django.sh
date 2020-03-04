#! /usr/bin/env bash

function usage() {
    echo "usage: start.sh <setup.env file> <gunicorn.cfg file>"
}

function err() {
    msg=$1
    echo "$1" 1>&2
    exit 1
}

if [ $# -ne 2 ]
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

cd ${DJANGO_PROJ_PATH} && python3 manage.py migrate && python3 manage.py collectstatic && cd -

exec gunicorn -c ${GUNICORN_CFG} --env DJANGO_SETTINGS_MODULE=Aves2.settings Aves2.wsgi
