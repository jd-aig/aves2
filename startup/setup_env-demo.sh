export CPU_NUMS=4

# Django
export DJANGO_DEBUG_MODE="no"  # yes/no
export DJANGO_PROJ_PATH="/src/aves2/Aves2"
export DJANGO_PORT="8080"
export DJANGO_APP_DB_HOST="aves2_mysql.aves2-sys"
export DJANGO_APP_DB_PORT="3306"
export DJANGO_APP_DB_NAME="aves2"
export DJANGO_APP_DB_USER="aves2"
export DJANGO_APP_DB_PASS="helloaves2"

# Aves
export AVES2_CLUSTER="swarm"
export AVES2_TRAIN_NETWORK="aves2-sys"
export DOCKER_URL="unix://var/run/docker.sock"
export AVES_URL_PREFIX="aves2"
export AVES_API_HOST="http://aves2_mysql.aves2-sys:8080/aves2/"
export AVES_LOGIN_URL="/aves2/accounts/login/"
export AVES_RUN_AS_ROOT="yes"  # yes/no
export AVES_JOB_LABEL="aves-training"

# Oss
export ENABLE_OSS="no"  # yes/no
export DEFAULT_S3_ACCESS_KEY_ID=""
export DEFAULT_S3_SECRET_ACCESS_KEY=""
export DEFAULT_S3_ENDPOINT=""

# RabbitMQ
export RABBITMQ_HOST="aves2_rabbitmq.aves2-sys"
export RABBITMQ_USER="aves2"
export RABBITMQ_PASS="helloaves2"
export STATUS_REPORT_EXCHANGE="ai.aves.status"
export STATUS_REPORT_EXCHANGE_TYPE="topic"
export STATUS_REPORT_ROUTING_KEY="status.aves"

# Celery
export C_FORCE_ROOT="yes"  # yes/no
export CELERY_BROKER_URL="amqp://aves2:helloaves2@aves2_rabbitmq.aves2-sys:5672//"
export CELERY_TASK_DEFAULT_QUEUE="aves2.celery"
export CELERY_CONCURRENCY=10

