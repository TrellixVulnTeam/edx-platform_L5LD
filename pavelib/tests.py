"""
Unit test tasks
"""
import os
import sys
from paver.easy import sh, task, cmdopts, needs
from pavelib.utils.test import suites
from pavelib.utils.envs import Env
from optparse import make_option

try:
    from pygments.console import colorize
except ImportError:
    colorize = lambda color, text: text  # pylint: disable-msg=invalid-name

__test__ = False  # do not collect


@task
@needs(
    'pavelib.prereqs.install_prereqs',
    'pavelib.utils.test.utils.clean_reports_dir',
)
@cmdopts([
    ("system=", "s", "System to act on"),
    ("test_id=", "t", "Test id"),
    ("failed", "f", "Run only failed tests"),
    ("fail_fast", "x", "Run only failed tests"),
    ("fasttest", "a", "Run without collectstatic"),
    make_option("--verbose", action="store_const", const=2, dest="verbosity"),
    make_option("-q", "--quiet", action="store_const", const=0, dest="verbosity"),
    make_option("-v", "--verbosity", action="count", dest="verbosity", default=1),
])
def test_system(options):
    """
    Run tests on our djangoapps for lms and cms
    """
    system = getattr(options, 'system', None)
    test_id = getattr(options, 'test_id', None)

    opts = {
        'failed_only': getattr(options, 'failed', None),
        'fail_fast': getattr(options, 'fail_fast', None),
        'fasttest': getattr(options, 'fasttest', None),
        'verbosity': getattr(options, 'verbosity', 1),
    }

    if test_id:
        if not system:
            system = test_id.split('/')[0]
        if system == 'common':
            system = 'lms'
        opts['test_id'] = test_id

    if test_id or system:
        system_tests = [suites.SystemTestSuite(system, **opts)]
    else:
        system_tests = []
        for syst in ('cms', 'lms'):
            system_tests.append(suites.SystemTestSuite(syst, **opts))

    test_suite = suites.PythonTestSuite('python tests', subsuites=system_tests, **opts)
    test_suite.run()


@task
@needs(
    'pavelib.prereqs.install_prereqs',
    'pavelib.utils.test.utils.clean_reports_dir',
)
@cmdopts([
    ("lib=", "l", "lib to test"),
    ("test_id=", "t", "Test id"),
    ("failed", "f", "Run only failed tests"),
    ("fail_fast", "x", "Run only failed tests"),
    make_option("--verbose", action="store_const", const=2, dest="verbosity"),
    make_option("-q", "--quiet", action="store_const", const=0, dest="verbosity"),
    make_option("-v", "--verbosity", action="count", dest="verbosity", default=1),
])
def test_lib(options):
    """
    Run tests for common/lib/ and pavelib/ (paver-tests)
    """
    lib = getattr(options, 'lib', None)
    test_id = getattr(options, 'test_id', lib)

    opts = {
        'failed_only': getattr(options, 'failed', None),
        'fail_fast': getattr(options, 'fail_fast', None),
        'verbosity': getattr(options, 'verbosity', 1),
    }

    if test_id:
        if '/' in test_id:
            lib = '/'.join(test_id.split('/')[0:3])
        else:
            lib = 'common/lib/' + test_id.split('.')[0]
        opts['test_id'] = test_id
        lib_tests = [suites.LibTestSuite(lib, **opts)]
    else:
        lib_tests = [suites.LibTestSuite(d, **opts) for d in Env.LIB_TEST_DIRS]

    test_suite = suites.PythonTestSuite('python tests', subsuites=lib_tests, **opts)
    test_suite.run()

    # Clear the Esperanto directory of any test artifacts
    sh('git checkout conf/locale/eo')


@task
@needs(
    'pavelib.prereqs.install_prereqs',
    'pavelib.utils.test.utils.clean_reports_dir',
)
@cmdopts([
    ("failed", "f", "Run only failed tests"),
    ("fail_fast", "x", "Run only failed tests"),
    make_option("--verbose", action="store_const", const=2, dest="verbosity"),
    make_option("-q", "--quiet", action="store_const", const=0, dest="verbosity"),
    make_option("-v", "--verbosity", action="count", dest="verbosity", default=1),
])
def test_python(options):
    """
    Run all python tests
    """
    opts = {
        'failed_only': getattr(options, 'failed', None),
        'fail_fast': getattr(options, 'fail_fast', None),
        'verbosity': getattr(options, 'verbosity', 1),
    }

    python_suite = suites.PythonTestSuite('Python Tests', **opts)
    python_suite.run()


@task
@needs(
    'pavelib.prereqs.install_prereqs',
    'pavelib.utils.test.utils.clean_reports_dir',
)
@cmdopts([
    make_option("--verbose", action="store_const", const=2, dest="verbosity"),
    make_option("-q", "--quiet", action="store_const", const=0, dest="verbosity"),
    make_option("-v", "--verbosity", action="count", dest="verbosity", default=1),
])
def test(options):
    """
    Run all tests
    """
    opts = {
        'verbosity': getattr(options, 'verbosity', 1)
    }
    # Subsuites to be added to the main suite
    python_suite = suites.PythonTestSuite('Python Tests', **opts)
    js_suite = suites.JsTestSuite('JS Tests', mode='run', with_coverage=True)

    # Main suite to be run
    all_unittests_suite = suites.TestSuite('All Tests', subsuites=[js_suite, python_suite])
    all_unittests_suite.run()


@task
@needs('pavelib.prereqs.install_prereqs')
@cmdopts([
    ("compare_branch", "b", "Branch to compare against, defaults to origin/master"),
])
def coverage(options):
    """
    Build the html, xml, and diff coverage reports
    """
    compare_branch = getattr(options, 'compare_branch', 'origin/master')

    for directory in Env.LIB_TEST_DIRS + ['cms', 'lms']:
        report_dir = Env.REPORT_DIR / directory

        if (report_dir / '.coverage').isfile():
            # Generate the coverage.py HTML report
            sh("coverage html --rcfile={dir}/.coveragerc".format(dir=directory))

            # Generate the coverage.py XML report
            sh("coverage xml -o {report_dir}/coverage.xml --rcfile={dir}/.coveragerc".format(
                report_dir=report_dir,
                dir=directory
            ))

    # Find all coverage XML files (both Python and JavaScript)
    xml_reports = []

    for filepath in Env.REPORT_DIR.walk():
        if filepath.basename() == 'coverage.xml':
            xml_reports.append(filepath)

    if not xml_reports:
        err_msg = colorize(
            'red',
            "No coverage info found.  Run `paver test` before running `paver coverage`.\n"
        )
        sys.stderr.write(err_msg)
    else:
        xml_report_str = ' '.join(xml_reports)
        diff_html_path = os.path.join(Env.REPORT_DIR, 'diff_coverage_combined.html')

        # Generate the diff coverage reports (HTML and console)
        sh(
            "diff-cover {xml_report_str} --compare-branch={compare_branch} "
            "--html-report {diff_html_path}".format(
                xml_report_str=xml_report_str,
                compare_branch=compare_branch,
                diff_html_path=diff_html_path,
            )
        )

        print("\n")
