FROM ubuntu:xenial-20200212

# Install python3
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        software-properties-common && \
    add-apt-repository ppa:jonathonf/python-3.6 -y && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        python3.6 python3.6-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pip
RUN wget --tries=3 https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py && \
    $PY3_BIN /tmp/get-pip.py && \
    pip3 install --no-cache-dir --upgrade pip==18.1.* && \
    apt-get update --fix-missing && \
    apt-get install -f --yes --no-install-recommends apt-transport-https lsb-release && \
    # Fix issue:  ModuleNotFoundError: No module named 'lsb_release'
    sed -i 's/python3/python3.5/' /usr/bin/lsb_release && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install mysqlclient
RUN wget --no-check-certificate http://dev.mysql.com/get/mysql-apt-config_0.7.3-1_all.deb && \
    dpkg -i mysql-apt-config_0.7.3-1_all.deb && \
    apt-get -y update && \
    $APT_INSTALL -y --force-yes libmysqlclient-dev && \
    $APT_INSTALL gcc && \
    $PIP3_INSTALL mysqlclient && \
    rm mysql-apt-config_0.7.3-1_all.deb && \
    apt-get autoremove -y --force-yes gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install python packages
RUN pip3 install \
    django==2.2 \
    djangorestframework==3.9.1 \
    django-filter==2.1.0 \
    django-mysql==2.4.1 \
    celery==4.2.1 \
    celery_once==2.0.0 \
    django_celery_results==1.0.4 \
    redis==3.2.0 \
    kubernetes==9.* \
    mysqlclient==1.4.2 \
    gunicorn==20.0.4 \
    jsonschema==3.0.2

# Copy aves2 to /src
RUN mkdir /src/
COPY aves2 /src/aves2
RUN cd /src/aves2 && \
    $PIP3_INSTALL -r requirement.txt
