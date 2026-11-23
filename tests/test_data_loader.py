import json

import pandas as pd
import pytest

from utils.data_loader import load_data, split_data


def test_demo_and_test_are_disjoint():
    df = pd.DataFrame({"item_id": [str(i) for i in range(30)]})
    train, demos, test = split_data(df, .2, 5, 19)
    assert set(demos.item_id).issubset(set(train.item_id))
    assert set(demos.item_id).isdisjoint(set(test.item_id))
    assert set(train.item_id).isdisjoint(set(test.item_id))


def test_load_data_collapses_consistent_duplicate_ids(tmp_path):
    path = tmp_path / "data.jsonl"
    rows = [
        {"item_id": "A", "title": "Product", "bullet_points": ["one"],
         "brand": "Acme", "color": "Black"},
        {"item_id": "A", "title": "Product", "bullet_points": ["one", "two"],
         "brand": " acme ", "color": "black"},
        {"item_id": "B", "title": "Other", "brand": "Beta", "color": "Blue"},
    ]
    path.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    df = load_data(str(path))
    assert df.item_id.tolist() == ["A", "B"]
    assert df.loc[df.item_id == "A", "bullet_points_text"].iloc[0] == "one two"
    assert df.attrs["duplicate_audit"]["duplicate_id_groups"] == 1
    assert df.attrs["duplicate_audit"]["rows_after_deduplication"] == 2


def test_load_data_excludes_conflicting_duplicate_labels(tmp_path):
    path = tmp_path / "data.jsonl"
    rows = [
        {"item_id": "A", "title": "Product", "brand": "Acme"},
        {"item_id": "A", "title": "Product", "brand": "Other"},
        {"item_id": "B", "title": "Other", "brand": "Beta"},
    ]
    path.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    df = load_data(str(path))
    assert df.item_id.tolist() == ["B"]
    assert df.attrs["duplicate_audit"]["conflicting_id_groups_excluded"] == 1


def test_load_data_rejects_missing_ids(tmp_path):
    path = tmp_path / "data.jsonl"
    path.write_text(json.dumps({"title": "No ID"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing/blank item_id"):
        load_data(str(path))


def test_load_data_fails_if_all_duplicate_ids_conflict(tmp_path):
    path = tmp_path / "data.jsonl"
    rows = [
        {"item_id": "A", "title": "Product", "brand": "Acme"},
        {"item_id": "A", "title": "Product", "brand": "Other"},
    ]
    path.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="No unambiguous rows remain"):
        load_data(str(path))
