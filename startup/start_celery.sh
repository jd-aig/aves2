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

ENV_FILE=$1

[ -f ${ENV_FILE} ] || err "${ENV_FILE} is not exist"
source ${ENV_FILE}

[ ! -z ${DJANGO_PROJ_PATH} ] || err "${DJANGO_PROJ_PATH} is not defined"

proj_name=`basename ${DJANGO_PROJ_PATH}`
[ ! -z ${CELERY_CONCURRENCY} ] || CELERY_CONCURRENCY=4
cd ${DJANGO_PROJ_PATH}
exec celery -A ${proj_name} worker --pool gevent -c ${CELERY_CONCURRENCY} -l info -E -Ofair
