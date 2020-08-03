import os
import tempfile
import uuid

import flask
from flask import request
from flask_wtf.csrf import CSRFProtect
import jinja2

from analysis import queries
from analysis import generate_report
from common import filestore_utils
from common import utils

app = flask.Flask(__name__)

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

csrf = CSRFProtect(app)

TEMPLATES_DIR = os.path.join(utils.ROOT_DIR, 'web', 'templates')
JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
)
INDEX_TEMPLATE_NAME = 'generate_reports.html'


@app.route('/')
def index():
    fuzzers_and_experiments = queries.get_fuzzers_and_experiments()
    fuzzers = sorted(
        set(fuzzer_and_experiment[0]
            for fuzzer_and_experiment in fuzzers_and_experiments))
    experiments = sorted(
        set(fuzzer_and_experiment[1]
            for fuzzer_and_experiment in fuzzers_and_experiments), reverse=True)
    return flask.render_template(INDEX_TEMPLATE_NAME, fuzzers=fuzzers, experiments=experiments)


def get_report_url(report_filestore_dir):
    gcs_scheme = 'gs://'
    assert report_filestore_dir.startswith(gcs_scheme)
    schemeless_report_dir = report_filestore_dir[len(gcs_scheme):]
    schemeless_report_path = os.path.join(schemeless_report_dir, 'index.html')
    return 'https://storage.googleapis.com/' + schemeless_report_path


def _generate_report(fuzzers_from_experiments):
    experiments = [
        fuzzer_from_experiment[1]
        for fuzzer_from_experiment in fuzzers_from_experiments
    ]
    filestore_rel_dir = str(uuid.uuid4())
    filestore_dir = os.path.join(os.environ['REPORT_FILESTORE'],
                                 filestore_rel_dir)

    with tempfile.TemporaryDirectory() as temp_dir:
        generate_report.generate_report(
            experiments,
            report_directory=temp_dir,
            fuzzers_from_experiments=fuzzers_from_experiments,
            quick=True,
            report_name='custom',
            drop_private=True)
        filestore_utils.rsync(temp_dir, filestore_dir, parallel=True)

    return get_report_url(filestore_dir)

@app.route('/generate', methods=['POST'])
def generate():
    form = dict(request.form)
    del form['csrf_token']
    print(form.keys())
    fuzzers_from_experiments = [
        tuple(k.split(',')) for k in form.keys()
    ]

    return flask.redirect(_generate_report(fuzzers_from_experiments))
