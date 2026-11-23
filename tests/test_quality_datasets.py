from backend.quality_datasets import load_general_benchmark, load_seller_support_tasks


def test_general_benchmark_dataset_is_valid_and_unique():
    rows = load_general_benchmark()
    assert len(rows) == 60
    assert len({row["case_id"] for row in rows}) == 60
    assert all(row["evaluation_criteria"] for row in rows)


def test_seller_support_dataset_is_valid_and_unique():
    rows = load_seller_support_tasks()
    assert len(rows) == 16
    assert len({row["task_id"] for row in rows}) == 16
    assert {row["category"] for row in rows} >= {"delivery", "returns", "refunds", "payment"}


def test_general_benchmark_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "duplicate.jsonl"
    row = (
        '{"case_id":"DUP","category":"test","difficulty":"easy",'
        '"prompt":"Question?","reference_answer":"Answer.",'
        '"evaluation_criteria":["correctness"]}'
    )
    path.write_text(row + "\n" + row + "\n", encoding="utf-8")
    try:
        load_general_benchmark(path)
    except ValueError as exc:
        assert "duplicate case_id" in str(exc)
    else:
        raise AssertionError("Expected duplicate case_id validation to fail")
