# LLM Prompt Benchmark — Experimental Results

- Provider: groq
- Model: openai/gpt-oss-20b
- Evaluation rows: 200
- Training rows: 6318
- Random seed: 42
- Run timestamp (UTC): 2026-11-23T13:27:35.964997+00:00

## Strategy comparison

| Strategy | Exact match | Micro F1 | Precision | Recall | JSON validity | Mean latency (ms) | Failed requests |
|---|---:|---:|---:|---:|---:|---:|---:|
| zero_shot | 0.000 | 0.064 | 0.113 | 0.044 | 0.635 | 4937.027 | 0.000 |
| few_shot | 0.000 | 0.163 | 0.476 | 0.098 | 0.215 | 9435.288 | 0.695 |
| cot | 0.000 | 0.005 | 0.083 | 0.003 | 0.040 | 38405.121 | 0.960 |
| structured | 0.000 | 0.007 | 0.200 | 0.003 | 0.025 | 53853.391 | 0.975 |
| role_based | 0.000 | 0.003 | 0.074 | 0.002 | 0.035 | 56576.655 | 0.965 |

## Attribute-level F1

| Strategy | brand | color | product_type | style | material | model_number |
|---|---:|---:|---:|---:|---:|---:|
| zero_shot | 0.204 | 0.114 | 0.000 | 0.013 | 0.030 | 0.000 |
| few_shot | 0.298 | 0.140 | 0.230 | 0.184 | 0.074 | 0.050 |
| cot | 0.019 | 0.000 | 0.000 | 0.000 | 0.000 | 0.010 |
| structured | 0.039 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| role_based | 0.010 | 0.010 | 0.000 | 0.000 | 0.000 | 0.000 |

## Paired comparisons against zero-shot

| Strategy | Mean exact-match difference | 95% bootstrap CI | Sign-test p-value | Wins / losses / ties |
|---|---:|---:|---:|---:|
| few_shot | 0.000 | [0.000, 0.000] | 1.0000 | 0 / 0 / 200 |
| cot | 0.000 | [0.000, 0.000] | 1.0000 | 0 / 0 / 200 |
| structured | 0.000 | [0.000, 0.000] | 1.0000 | 0 / 0 / 200 |
| role_based | 0.000 | [0.000, 0.000] | 1.0000 | 0 / 0 / 200 |

## Interpretation and limitations

- Exact match requires all six attributes to match; interpret it alongside attribute-level F1.
- Paired confidence intervals compare strategies on the same held-out records.
- The paired sign test is two-sided and excludes ties.
- Unsupported-attribute rate is a lexical evidence heuristic, not semantic fact verification.
- API request failures and provider rate limits can affect effective sample size; inspect raw rows.
- Results apply to this dataset split, model, provider and configuration; they do not establish universal superiority.

Raw run artifact: results/groq_openai_gpt-oss-20b_20261123T132735Z.json
