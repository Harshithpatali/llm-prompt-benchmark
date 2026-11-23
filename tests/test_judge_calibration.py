from backend.judge_calibration import calculate_calibration

def test_perfect_agreement_is_reliable_with_enough_samples():
    rows=[{"component_id":"C1","parent_category":"Safety","criterion_name":"Safety","judge_verdict":"pass","human_verdict":"pass"} for _ in range(6)]
    report=calculate_calibration(rows,min_samples=5)
    assert report["overall"]["exact_agreement"]==1.0
    assert report["overall"]["cohen_kappa"]==1.0
    assert report["criteria"][0]["reliability_status"]=="reliable"

def test_disagreement_flags_criterion():
    rows=[{"component_id":"C2","parent_category":"Safety","criterion_name":"Safety","judge_verdict":"pass","human_verdict":"fail"} for _ in range(6)]
    report=calculate_calibration(rows,min_samples=5)
    assert report["criteria"][0]["exact_agreement"]==0.0
    assert report["criteria"][0]["reliability_status"]=="review"

def test_small_sample_is_not_called_reliable():
    rows=[{"component_id":"C3","parent_category":"Safety","criterion_name":"Safety","judge_verdict":"pass","human_verdict":"pass"} for _ in range(2)]
    report=calculate_calibration(rows,min_samples=5)
    assert report["criteria"][0]["reliability_status"]=="insufficient_data"
