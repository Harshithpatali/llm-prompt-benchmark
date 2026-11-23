import csv
import io

from backend.rubric_qa import HEADERS, OVERALL_ROWS, validate_csv

def make_csv():
    rows = [HEADERS]
    for i in range(1, 51):
        rows.append([f"C{i}","Content Quality & Domain Knowledge","Facts","Factual accuracy",
                     "Does the response use supported facts?","Explicit","Use supported facts","N/A",
                     "Fail if an unsupported factual claim is made"])
    for item in OVERALL_ROWS:
        rows.append([item[0],"Overall Performance",item[1],item[2],item[3],"N/A","N/A","N/A","N/A"])
    out=io.StringIO()
    csv.writer(out,quoting=csv.QUOTE_ALL).writerows(rows)
    return out.getvalue()

def test_valid_csv_passes():
    result=validate_csv(make_csv())
    assert result["status"]=="PASS"
    assert result["counts"]["atomic_components"]==50
    assert result["counts"]["overall_components"]==14

def test_missing_overall_component_fails():
    content=make_csv()
    rows=list(csv.reader(io.StringIO(content)))
    rows.pop()
    out=io.StringIO()
    csv.writer(out,quoting=csv.QUOTE_ALL).writerows(rows)
    result=validate_csv(out.getvalue())
    assert result["status"]=="FAIL"
    assert any("O1 through O14" in issue["message"] for issue in result["issues"])

def test_explicit_implicit_mismatch_fails():
    rows=list(csv.reader(io.StringIO(make_csv())))
    rows[1][6]="N/A"
    out=io.StringIO()
    csv.writer(out,quoting=csv.QUOTE_ALL).writerows(rows)
    assert validate_csv(out.getvalue())["status"]=="FAIL"

def test_wrong_parent_category_fails():
    rows=list(csv.reader(io.StringIO(make_csv())))
    rows[1][1]="Content Quality"
    out=io.StringIO()
    csv.writer(out,quoting=csv.QUOTE_ALL).writerows(rows)
    assert validate_csv(out.getvalue())["status"]=="FAIL"
