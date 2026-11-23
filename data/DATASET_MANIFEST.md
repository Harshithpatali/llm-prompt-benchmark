# Dataset Manifest

This manifest records the datasets included in the consolidated repository. Dataset-specific licenses and upstream provenance must be checked before redistribution or commercial use.

| Dataset | File | Rows / records | Purpose | Provenance and limitations |
|---|---|---:|---|---|
| E-commerce product attributes | `data/final_clean_amazon.jsonl` | Validate with the dataset loader before each experiment | Structured extraction benchmark with six gold attributes | Existing repository asset. Confirm upstream source, license, collection method, and label provenance before making external claims. |
| General response benchmark | `data/benchmark.jsonl` | 60 | General response-quality challenge cases across several categories | Copied from the companion LLM Quality Intelligence Platform repository. Starter portfolio cases, not an externally validated gold standard. |
| Seller-support scenarios | `data/seller_support_tasks.json` | 16 | Policy, privacy, delivery, returns, refunds, payment, and product-support review scenarios | Copied from the companion repository. Illustrative scenarios, not real customer records. The `response` field is a supplied example response and may intentionally contain errors; `expected` describes the review objective. |

## Evaluation safeguards

- Preserve dataset files as versioned source assets; do not silently rewrite labels during evaluation.
- Record a file hash, dataset version, and row count in each experiment artifact.
- Split related examples together where there is a risk of leakage.
- Do not treat reference-answer lexical overlap as semantic correctness or factuality.
- Keep task-specific metrics separate. Product extraction F1, general response rubric scores, and seller-support policy outcomes are not directly comparable.
- Collect independent human annotations before claiming judge reliability or calibration performance.
- The companion repository's top-level MIT license does not by itself establish that every upstream dataset has a separate redistribution license.
