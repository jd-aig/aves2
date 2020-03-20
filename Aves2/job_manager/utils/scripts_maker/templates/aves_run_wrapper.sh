#! /bin/bash

[ ! -d /AVES/log/ ] && mkdir -p /AVES/log/
bash /aves_bin/aves_run.sh "$@" 2>&1 | tee /AVES/log/${AVES_WORK_ROLE}_${AVES_WORK_INDEX}.log
