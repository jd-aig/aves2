FROM ubuntu:xenial-20200212

# Install python3
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        python3.6 python3.6-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pip
RUN wget --tries=3 https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py && \
    python3 /tmp/get-pip.py && \
    pip3 install --no-cache-dir --upgrade pip==18.1.* && \
    apt-get update --fix-missing && \
    apt-get install -f --yes --no-install-recommends apt-transport-https lsb-release && \
    sed -i 's/python3/python3.5/' /usr/bin/lsb_release && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install mysqlclient
ARG DEBIAN_FRONTEND=noninteractive
RUN wget --no-check-certificate http://dev.mysql.com/get/mysql-apt-config_0.7.3-1_all.deb && \
    dpkg -i mysql-apt-config_0.7.3-1_all.deb && \
    apt-get -y update && \
    apt-get install -y --force-yes libmysqlclient-dev \
    gcc && \
    pip3 install  mysqlclient && \
    rm mysql-apt-config_0.7.3-1_all.deb && \
    apt-get autoremove -y --force-yes gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN pip3 install   mysqlclient==1.4.2

# Install python packages
# RUN pip3 install \
#     django==2.2 \
#     djangorestframework==3.9.1 \
#     django-filter==2.1.0 \
#     django-mysql==2.4.1 \
#     celery==4.2.1 \
#     celery_once==2.0.0 \
#     django_celery_results==1.0.4 \
#     redis==3.2.0 \
#     kubernetes==9.* \
#     gunicorn==20.0.4 \
#     jsonschema==3.0.2

# Copy aves2 to /src
RUN mkdir /src/
COPY aves2 /src/aves2
RUN cd /src/aves2 && \
    pip3 install -r requirement.txt
