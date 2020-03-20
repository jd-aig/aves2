export CPU_NUMS=4

# Django
export DJANGO_DEBUG_MODE="no"  # yes/no
export DJANGO_PROJ_PATH=""
export DJANGO_PORT="80"
export DJANGO_APP_DB_HOST=""
export DJANGO_APP_DB_PORT="3306"
export DJANGO_APP_DB_NAME=""
export DJANGO_APP_DB_USER=""
export DJANGO_APP_DB_PASS=""

# Aves
export AVES_URL_PREFIX="aves2"
export AVES_API_HOST=""
export AVES_RUN_AS_ROOT="yes"  # yes/no
export AVES_JOB_LABEL="aves-training"

# Oss
export ENABLE_OSS="yes"  # yes/no
export DEFAULT_S3_ACCESS_KEY_ID=""
export DEFAULT_S3_SECRET_ACCESS_KEY=""
export DEFAULT_S3_ENDPOINT=""

# RabbitMQ
export RABBITMQ_HOST=""
export RABBITMQ_USER=""
export RABBITMQ_PASS=""
export STATUS_REPORT_EXCHANGE="ai.aves.status"
export STATUS_REPORT_EXCHANGE_TYPE="topic"
export STATUS_REPORT_ROUTING_KEY="status.aves"

# Celery
export C_FORCE_ROOT="yes"  # yes/no
export CELERY_BROKER_URL=""
export CELERY_TASK_DEFAULT_QUEUE="aves2.celery"
export CELERY_CONCURRENCY=10
