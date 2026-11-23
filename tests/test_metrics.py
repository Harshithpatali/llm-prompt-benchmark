import pytest
from evaluation.metrics import evaluate_batch, safe_parse_json, paired_bootstrap_ci, paired_sign_test

def test_json_parser():
    assert safe_parse_json('```json\n{"brand":"Nike"}\n```')=={"brand":"Nike"}
    assert safe_parse_json('prefix {"brand":"Nike"} suffix')=={"brand":"Nike"}
    assert safe_parse_json("no json")=={}

def test_metrics_and_missing_values():
    result=evaluate_batch([{"brand":" NIKE ","color":None}],[{"brand":"Nike","color":"Black"}],['{"brand":"Nike"}'],["Nike shoe"])
    assert result["per_attribute"]["brand"]["f1"]==1
    assert result["missing_attribute_rate"]>0
    assert result["json_validity_rate"]==1

def test_length_mismatch():
    with pytest.raises(ValueError): evaluate_batch([{}],[])

def test_paired_statistics():
    a=[1,1,0,1]; b=[0,1,0,0]
    assert paired_bootstrap_ci(a,b,iterations=100,seed=2)==paired_bootstrap_ci(a,b,iterations=100,seed=2)
    assert paired_sign_test(a,b)["wins"]==2
