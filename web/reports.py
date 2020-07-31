import os
import tempfile

import flask
from flask import request
import jinja2

from analysis import queries
from analysis import generate_report
from common import utils


app = flask.Flask(__name__)

TEMPLATES_DIR = os.path.join(utils.ROOT_DIR, 'web', 'templates')
JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
)


@app.route('/')
def index():
    template_name = 'generate_reports.html'
    template = JINJA_ENV.get_template(template_name)
    fuzzers_and_experiments = queries.get_fuzzers_and_experiments()
    fuzzers = sorted(set(fuzzer_and_experiment[0] for fuzzer_and_experiment in fuzzers_and_experiments))
    experiments = sorted(set(fuzzer_and_experiment[1] for fuzzer_and_experiment in fuzzers_and_experiments))
    return template.render(fuzzers=fuzzers, experiments=experiments)


@app.route('/generate', methods=['POST'])
def generate():
    temp_directory = '/tmp/tmpdir' # tempfile.TemporaryDirectory()
    fuzzers_from_experiments = [
        tuple(k.split(',')) for k in request.form.keys()]
    experiments = [fuzzer_from_experiment[1] for fuzzer_from_experiment in fuzzers_from_experiments]
    generate_report.generate_report(
        experiments, report_directory=temp_directory,
        fuzzers_from_experiments=fuzzers_from_experiments,
        quick=True,
        report_name='custom',
        drop_private=True)
    return 'done'
