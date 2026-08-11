"""Every pipeline script must actually load, and the chain must actually run.

This file exists because the same defect got through three times. Numbering the
scripts broke `import prepare_field_data` and `import export_gama_zones` -- a
Python module name cannot start with a digit -- and two of the three occurrences
survived review because the checks only inspected module-level imports. The third
sat inside `main()`, where no static scan was looking.

The lesson taken here is that the guard has to execute, not read. `make results`
failing at its last step is the only thing that found it.
"""

import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parents[1]
SCRIPTS = sorted((ROOT / 'scripts').glob('[0-9][0-9]_*.py'))


def test_every_pipeline_step_is_present():
    """The numbering is the pipeline documentation; a gap means a missing step."""
    numbers = sorted(int(p.name[:2]) for p in SCRIPTS)
    assert numbers == list(range(1, 12)), f'expected 01..11, found {numbers}'


@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.name)
def test_script_imports_cleanly(script, monkeypatch):
    """Load each script as a module, executing its top level.

    This catches a broken import, a missing package dependency and a path constant
    that no longer resolves. It does not run `main()`: the scripts are guarded by
    `if __name__ == '__main__'`, and loading them under another name leaves that
    block untouched.
    """
    monkeypatch.chdir(ROOT)
    spec = importlib.util.spec_from_file_location(f'_probe_{script.stem}', script)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        # A script may refuse to load when an unpublished input is missing --
        # 02_count_vehicles needs the videos. That is a deliberate early exit,
        # not an import failure.
        pass


def test_no_script_imports_a_numbered_sibling_by_name():
    """`import 01_prepare_field_data` is not valid Python and never will be.

    Numbered scripts that need each other must load by file path. Checked as text,
    including inside function bodies, which is where the third occurrence hid.
    """
    offenders = []
    for script in SCRIPTS + sorted((ROOT / 'scripts' / 'experiments').glob('*.py')):
        text = script.read_text(encoding='utf-8')
        for old in ('import prepare_field_data', 'import export_gama_zones',
                    'import evaluate_models', 'import build_field_map',
                    'import build_report', 'import calibrate_emissions'):
            if old in text and 'load_script' not in text:
                offenders.append(f'{script.name}: {old}')
    assert not offenders, (
        'these scripts import a renamed sibling by module name:\n  ' + '\n  '.join(offenders))


@pytest.mark.slow
def test_full_chain_runs():
    """Run the reproducible chain end to end.

    Opt-in: takes several minutes and rewrites results/. Run it with
    `pytest -m slow` before publishing, or whenever a script is renamed.
    """
    env = dict(os.environ, PYTHON=sys.executable)
    proc = subprocess.run(['make', 'results', f'PYTHON={sys.executable}'],
                          cwd=ROOT, capture_output=True, text=True, env=env, timeout=3600)
    assert proc.returncode == 0, (
        f'`make results` failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}')
