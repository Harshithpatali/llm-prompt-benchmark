import pandas as pd
from utils.data_loader import split_data

def test_demo_and_test_are_disjoint():
    df=pd.DataFrame({"item_id":[str(i) for i in range(30)]})
    train,demos,test=split_data(df,.2,5,19)
    assert set(demos.item_id).issubset(set(train.item_id))
    assert set(demos.item_id).isdisjoint(set(test.item_id))
    assert set(train.item_id).isdisjoint(set(test.item_id))
