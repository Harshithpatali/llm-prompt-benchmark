import pandas as pd

def load_data(path="data/final_clean_amazon.jsonl"):
    df=pd.read_json(path,lines=True)
    if "item_id" not in df: raise ValueError("Dataset must contain item_id")
    if df.item_id.astype(str).duplicated().any(): raise ValueError("item_id must be unique")
    if "item_name" not in df and "title" in df: df=df.rename(columns={"title":"item_name"})
    if "bullet_points_text" not in df:
        col=df.get("bullet_points",pd.Series([""]*len(df),index=df.index))
        df["bullet_points_text"]=col.apply(lambda x:" ".join(map(str,x)) if isinstance(x,list) else str(x or ""))
    return df

def split_data(df,test_size=.2,demo_size=4,seed=42):
    if not 0<test_size<1: raise ValueError("test_size must be between 0 and 1")
    shuffled=df.sample(frac=1,random_state=seed).reset_index(drop=True)
    n=max(1,int(round(len(shuffled)*test_size)))
    if len(shuffled)-n<1: raise ValueError("At least two rows are required")
    test=shuffled.iloc[:n].copy(); train=shuffled.iloc[n:].copy()
    demos=train.sample(n=min(demo_size,len(train)),random_state=seed).copy()
    assert set(demos.item_id.astype(str)).isdisjoint(set(test.item_id.astype(str)))
    return train,demos,test

def prepare_examples(df,n=4):
    out=[]
    for _,r in df.head(n).iterrows():
        out.append({"item_name":r.get("item_name",""),"bullet_points":r.get("bullet_points_text",""),
                    "gold":{k:r.get(k) for k in ("brand","color","product_type","style","material","model_number")}})
    return out

def gold_record(row):
    return {k:row.get(k) for k in ("brand","color","product_type","style","material","model_number")}
