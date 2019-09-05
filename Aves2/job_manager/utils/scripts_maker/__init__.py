#! /usr/bin/env python

import os
import json
import argparse

from jinja2 import PackageLoader, Environment, FileSystemLoader


def gen_aves_run_script(data_params):
    tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(tpl_path))
    tpl = env.get_template(os.path.join('aves_run.sh.tmpl'))

    context = {
        'data_params': data_params
    }
    return tpl.render(context)

def gen_config_aws_script():
    tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
    with open(os.path.join(tpl_path, 'aves_config_aws.sh')) as f:
        return f.read()

def gen_aves_dist_envs_script():
    tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
    with open(os.path.join(tpl_path, 'aves_get_dist_envs.py')) as f:
        return f.read()

