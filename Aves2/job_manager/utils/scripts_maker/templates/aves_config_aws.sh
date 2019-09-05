#! /usr/bin/env bash

profile_name=$1
s3_ak=$2
s3_sk=$3

[ ! -d ~/.aws ] && mkdir ~/.aws

echo "[${profile_name}]" >> ~/.aws/config
echo "[${profile_name}]" >> ~/.aws/credentials
echo "aws_access_key_id=${s3_ak}" >> ~/.aws/credentials
echo "aws_secret_access_key=${s3_sk}" >> ~/.aws/credentials
echo "" >> ~/.aws/credentials

