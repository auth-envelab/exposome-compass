from pathlib import Path


def test_public_source_has_no_embedded_old_project_history_or_raw_data():
    root=Path(__file__).resolve().parents[1]
    assert not (root/'PRODUCT_PLAN.txt').exists()
    assert not (root/'research').exists()
    assert not (root/'data').exists()
    assert not (root/'results').exists()
    assert (root/'README.md').is_file()
    assert (root/'src'/'exposome_compass'/'scoring.py').is_file()
