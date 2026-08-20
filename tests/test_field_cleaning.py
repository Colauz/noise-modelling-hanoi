"""Field cleaning: who a measurement came from, and what survives to publication.

Opening the survey to the public broke an assumption the cleaning had always
been allowed to make. `collector` held one of three names, so `(collector,
timestamp)` identified a measurement. Every submission from the mobile app
carries the single value `public`, and two contributors who happened to submit
on the same timestamp would have collapsed into one row -- silently, and only
once real public data arrived.

This file also guards the property that makes the app's contributor identifier
acceptable at all: it is used for cleaning and never published.
"""

import importlib.util
import pathlib

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).parents[1]
SCRIPT = ROOT / 'scripts' / '01_prepare_field_data.py'


@pytest.fixture(scope='module')
def prepare():
    """`import 01_prepare_field_data` is not valid Python; load it by path."""
    spec = importlib.util.spec_from_file_location('_field_cleaning', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(rows):
    """A minimal standardised frame, as `standardize` would hand it to `clean`."""
    base = {
        'latitude': 21.0317, 'longitude': 105.8514, 'accuracy': 4.9,
        'noise_dB': 70.0, 'class': 'Transportation noise', 'site': 'Hoan Kiem lake',
        'collector': 'lucas', 'dist_to_road': '0-2 m',
    }
    return pd.DataFrame([{**base, **r} for r in rows])


T1 = pd.Timestamp('2026-08-20 17:30:00.100')
T2 = pd.Timestamp('2026-08-20 17:30:00.200')


def test_the_campaign_points_still_key_on_the_collector(prepare):
    """The 363 predate `contributor_id` and must clean exactly as before."""
    df = frame([
        {'timestamp': T1, 'collector': 'lucas'},
        {'timestamp': T1, 'collector': 'lucas'},      # a genuine duplicate
        {'timestamp': T1, 'collector': 'laurian'},    # a second collector, same instant
    ])
    cleaned = prepare.clean(df)
    assert len(cleaned) == 2
    assert set(cleaned['collector']) == {'lucas', 'laurian'}


def test_two_public_contributors_at_one_instant_are_two_measurements(prepare):
    """The defect this change exists for."""
    df = frame([
        {'timestamp': T1, 'collector': 'public', 'contributor_id': 'aaa'},
        {'timestamp': T1, 'collector': 'public', 'contributor_id': 'bbb'},
    ])
    cleaned = prepare.clean(df)
    assert len(cleaned) == 2, 'two contributors were merged into one row'


def test_one_contributor_submitting_twice_is_still_de_duplicated(prepare):
    df = frame([
        {'timestamp': T1, 'collector': 'public', 'contributor_id': 'aaa'},
        {'timestamp': T1, 'collector': 'public', 'contributor_id': 'aaa'},
        {'timestamp': T2, 'collector': 'public', 'contributor_id': 'aaa'},
    ])
    cleaned = prepare.clean(df)
    assert len(cleaned) == 2


def test_a_mixed_export_keys_each_row_on_what_it_has(prepare):
    """Campaign rows and app rows arrive in the same export once both are live."""
    df = frame([
        {'timestamp': T1, 'collector': 'lucas', 'contributor_id': np.nan},
        {'timestamp': T1, 'collector': 'public', 'contributor_id': 'aaa'},
        {'timestamp': T1, 'collector': 'public', 'contributor_id': '  '},   # blank, not an id
    ])
    key = prepare.dedup_key(df)
    assert list(key) == ['lucas', 'aaa', 'public']


def test_the_contributor_identifier_is_never_published(prepare, tmp_path):
    """`measurements.csv` carries no collector name and no device identifier."""
    df = frame([{'timestamp': T1, 'collector': 'public', 'contributor_id': 'aaa'}])
    cleaned = prepare.clean(df)
    out = tmp_path / 'measurements.csv'
    prepare.save_measurements(cleaned, out=out)
    header = out.read_text().splitlines()[0]
    assert 'contributor_id' not in header
    assert 'collector' not in header


def test_the_decibel_bounds_of_the_form_are_enforced(prepare):
    """The XLSForm constrains 20..120; cleaning is the second line of defence."""
    df = frame([
        {'timestamp': T1, 'noise_dB': 19.0},
        {'timestamp': T2, 'noise_dB': 121.0},
        {'timestamp': pd.Timestamp('2026-08-20 17:31:00'), 'noise_dB': 70.0},
    ])
    cleaned = prepare.clean(df)
    assert list(cleaned['noise_dB']) == [70.0]


def test_the_per_collector_offset_is_applied(prepare, monkeypatch):
    monkeypatch.setattr(prepare, 'CALIBRATION_OFFSET', {'lucas': 1.5, 'public': 0.0})
    df = frame([
        {'timestamp': T1, 'collector': 'lucas', 'noise_dB': 70.0},
        {'timestamp': T2, 'collector': 'public', 'noise_dB': 70.0},
    ])
    cleaned = prepare.clean(df).sort_values('timestamp')
    assert list(cleaned['noise_dB']) == [71.5, 70.0]
