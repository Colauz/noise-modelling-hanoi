"""The GAMA model must keep loading the same data after any edit.

This file exists because the model's inputs have been moved once and its text
rewritten twice, and each time the only way to know nothing had broken was to run
it. The check is now written down.

**It compares extracted VALUES, never literal strings.** The console wording has
already changed once — the user-interface strings were translated from French to
English on 2026-08-11 — and a test that broke on every relabelling would have been
disabled within a month. Both fingerprints are kept in `fixtures/`: the French one
as the continuity trace, the English one as the current reference. Their numbers
are identical, and that is the assertion.

Running GAMA is not part of the normal test run: it needs the GAMA platform and
takes about a minute per zone. To refresh the reference:

    gama-headless.sh -xml hanoi_noise_sim simulation/gama/hanoi_noise.gaml p.xml
    # set finalStep=3 in p.xml, then run it per zone and collect console-outputs
"""

import pathlib
import re

import pytest

FIXTURES = pathlib.Path(__file__).parent / 'fixtures'
FR = FIXTURES / 'gama-fingerprint-fr-2026-08-11.txt'
EN = FIXTURES / 'gama-fingerprint-en-2026-08-11.txt'

#: What the model must report at startup, per zone. These are the figures that
#: the whole simulation rests on: get them wrong and every scenario is wrong.
EXPECTED = {
    'Ocean Park': dict(cells=2544, roads=766, buildings=1075, measures=184, corridor=366),
    'Hoan Kiem':  dict(cells=1763, roads=673, buildings=10241, measures=99, corridor=205),
    'Vinh Tuy':   dict(cells=1280, roads=503, buildings=191,  measures=80, corridor=190),
}

#: The published grid, cross-checked against results/maps/hanoi_noise_map.csv.
TOTAL_CELLS = 5587


def _numbers(path: pathlib.Path) -> list[str]:
    """Every numeric token of a fingerprint, comments stripped."""
    body = '\n'.join(l for l in path.read_text(encoding='utf-8').splitlines()
                     if not l.startswith('#'))
    return re.findall(r'-?\d+\.?\d*(?:[Ee]-?\d+)?', body)


def test_both_fingerprints_exist():
    assert FR.exists() and EN.exists()


def test_translating_the_interface_changed_no_number():
    """The 2026-08-11 FR->EN string translation must be text-only.

    This is the assertion the two fixtures exist for.
    """
    fr, en = _numbers(FR), _numbers(EN)
    assert len(fr) == len(en), (
        f'the two fingerprints hold a different number of values ({len(fr)} vs {len(en)}): '
        f'something other than wording changed'
    )
    assert fr == en, [f'{a} -> {b}' for a, b in zip(fr, en) if a != b]


@pytest.mark.parametrize('zone', sorted(EXPECTED))
def test_zone_loads_the_expected_geometry(zone):
    """Values are read from the current fingerprint, whatever the wording around them."""
    text = EN.read_text(encoding='utf-8')
    block = next((b for b in text.split('Zone ') if b.startswith(zone)), None)
    assert block, f'{zone} missing from the fingerprint'

    exp = EXPECTED[zone]
    found = [int(n) for n in re.findall(r'(\d+)\s+(?:cells|roads|buildings)', block)]
    assert found[:3] == [exp['cells'], exp['roads'], exp['buildings']], (
        f'{zone}: geometry changed. Expected '
        f"{exp['cells']}/{exp['roads']}/{exp['buildings']}, read {found[:3]}"
    )

    measures = int(re.search(r'(\d+) field measurements', block).group(1))
    assert measures == exp['measures']

    corridor = int(re.search(r'corridor\s*:\s*(\d+) of', block).group(1))
    assert corridor == exp['corridor'], (
        f'{zone}: the measured corridor changed. FLOW_RADIUS restricts injected flow to '
        f'roads within 150 m of a measurement; a change here means that restriction moved.'
    )


def test_cells_sum_to_the_published_grid():
    assert sum(z['cells'] for z in EXPECTED.values()) == TOTAL_CELLS


def test_physical_kernel_is_the_delivered_one():
    """The kernel coefficients printed at startup come from models/hybrid_physical.json."""
    import json
    phys = json.loads((pathlib.Path(__file__).parents[1] / 'models' /
                       'hybrid_physical.json').read_text(encoding='utf-8'))
    text = EN.read_text(encoding='utf-8')
    a_hw = float(re.search(r'A_hw=([\d.E+-]+)', text).group(1))
    a_res = float(re.search(r'A_res=([\d.E+-]+)', text).group(1))
    assert a_hw == pytest.approx(phys['A_highway'], rel=1e-6)
    assert a_res == pytest.approx(phys['A_residential'], rel=1e-6)
    assert phys['apply_residual'] is False, (
        'the residual is applied: the map is no longer physics-only, and the model header '
        'plus docs/methodology.md both state that it is not'
    )
