"""Dataset loading with deterministic duplicate-ID auditing."""
import pandas as pd

TARGET_COLUMNS = ("brand", "color", "product_type", "style", "material", "model_number")


def _normalise_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def load_data(path="data/final_clean_amazon.jsonl"):
    df = pd.read_json(path, lines=True)
    input_rows = int(len(df))
    if "item_id" not in df:
        raise ValueError("Dataset contains missing/blank item_id column")
    if "item_name" not in df and "title" in df:
        df = df.rename(columns={"title": "item_name"})
    if "bullet_points_text" not in df:
        col = df.get("bullet_points", pd.Series([""] * len(df), index=df.index))
        df["bullet_points_text"] = col.apply(
            lambda x: " ".join(map(str, x)) if isinstance(x, (list, tuple)) else str(x or "")
        )

    df = df.copy()
    df["item_id"] = df["item_id"].astype("string").str.strip()
    missing_ids = int(df["item_id"].isna().sum() + df["item_id"].eq("").sum())
    if missing_ids:
        raise ValueError(f"Dataset contains {missing_ids} rows with missing/blank item_id")

    duplicate_rows = int(df["item_id"].duplicated(keep=False).sum())
    duplicate_groups = int(df.loc[df["item_id"].duplicated(keep=False), "item_id"].nunique())
    conflicting_ids = []
    kept = []

    # A product ID with contradictory gold labels is ambiguous and is excluded
    # entirely. Consistent duplicates retain the most informative source row.
    for item_id, group in df.groupby("item_id", sort=False):
        if len(group) == 1:
            kept.append(group.index[0])
            continue

        available_targets = [c for c in TARGET_COLUMNS if c in group.columns]
        signatures = {
            tuple(_normalise_value(row.get(c)) for c in available_targets)
            for _, row in group.iterrows()
        }
        if len(signatures) > 1:
            conflicting_ids.append(str(item_id))
            continue

        completeness_cols = [
            c for c in ("item_name", "bullet_points_text", *TARGET_COLUMNS)
            if c in group.columns
        ]
        scores = group[completeness_cols].apply(
            lambda row: sum(bool(_normalise_value(v)) for v in row), axis=1
        )
        bullet_lengths = group.get(
            "bullet_points_text", pd.Series("", index=group.index)
        ).fillna("").astype(str).str.len()
        title_lengths = group.get(
            "item_name", pd.Series("", index=group.index)
        ).fillna("").astype(str).str.len()
        ranking = pd.DataFrame({
            "completeness": scores,
            "bullet_length": bullet_lengths,
            "title_length": title_lengths,
        }, index=group.index)
        # Prefer completeness, then richer source text; stable sort preserves
        # the earliest source row when all quality signals are tied.
        selected = ranking.sort_values(
            ["completeness", "bullet_length", "title_length"],
            ascending=[False, False, False],
            kind="stable",
        ).index[0]
        kept.append(selected)

    df = df.loc[kept].copy().reset_index(drop=True)
    audit = {
        "input_rows": input_rows,
        "duplicate_id_groups": duplicate_groups,
        "duplicate_rows_involved": duplicate_rows,
        "conflicting_id_groups_excluded": len(conflicting_ids),
        "rows_after_deduplication": int(len(df)),
        "missing_id_rows_rejected": missing_ids,
    }
    df.attrs["duplicate_audit"] = audit
    if df.empty:
        raise ValueError(
            "No unambiguous rows remain after duplicate item_id cleaning. "
            "Inspect conflicting duplicate IDs and their gold labels."
        )
    if df["item_id"].duplicated().any():
        raise AssertionError("Internal error: item_id deduplication did not produce unique IDs")
    print("Dataset duplicate audit:", audit)
    if conflicting_ids:
        preview = ", ".join(conflicting_ids[:10])
        print(
            f"Excluded {len(conflicting_ids)} item_id groups with conflicting gold labels. "
            f"First IDs: {preview}"
        )
    return df


def split_data(df, test_size=.2, demo_size=4, seed=42):
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if "item_id" not in df or df.item_id.astype(str).duplicated().any():
        raise ValueError("split_data requires unique item_id values; call load_data first")
    shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    n = max(1, int(round(len(shuffled) * test_size)))
    if len(shuffled) - n < 1:
        raise ValueError("At least two rows are required")
    test = shuffled.iloc[:n].copy()
    train = shuffled.iloc[n:].copy()
    demos = train.sample(n=min(demo_size, len(train)), random_state=seed).copy()
    assert set(demos.item_id.astype(str)).isdisjoint(set(test.item_id.astype(str)))
    return train, demos, test


def prepare_examples(df, n=4):
    out = []
    for _, r in df.head(n).iterrows():
        out.append({
            "item_name": r.get("item_name", ""),
            "bullet_points": r.get("bullet_points_text", ""),
            "gold": {k: r.get(k) for k in TARGET_COLUMNS},
        })
    return out


def gold_record(row):
    return {k: row.get(k) for k in TARGET_COLUMNS}
