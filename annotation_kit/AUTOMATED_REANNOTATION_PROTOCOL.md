# Original 800-item automated re-annotation: protocol and provenance

This record documents the automated EXACT/NARROW re-annotation that produced
the reported DisTEMIST agreement of Cohen's kappa 0.8416 (*n* = 800). It is an
automated rubric-consistency check, not a human inter-annotator study.

## Execution record

- Execution date: 5 July 2026 KST; the final `iaa_full.csv` was saved at
  09:05:26 KST.
- Runtime model alias: `claude-sonnet-5`. The analysis environment resolved
  the endpoint dynamically with `MODEL = host.reasoning_model()` and printed
  `reasoning: claude-sonnet-5` immediately before the run.
- Model-version boundary: the endpoint did not expose an immutable dated build
  or revision, so none is inferred here.
- Blindness: each request contained only the English mention, linked concept
  label and linked concept code. The native EXACT/NARROW label was retained
  only for the later agreement calculation and was not inserted into the
  system or item prompt.
- Invocation: two batches of 400 requests, `max_tokens=200`,
  `max_concurrency=24`, with forced structured `annotate` tool output. Ten
  initially unparsed or truncated responses were retried with
  `max_tokens=500` and `max_concurrency=12`.
- Temperature: the request did not pass a temperature parameter. The platform
  default applied, and its numeric value was not recorded.

## Exact system rubric

```text
You are an expert clinical terminologist performing a GRANULARITY-RELATION annotation between a clinical mention and the SNOMED CT concept it was linked to. Decide one relation:

- NARROW: the clinical mention is MORE SPECIFIC than the assigned SNOMED concept. The concept is a broader/parent concept and the mention adds specificity the code lacks (laterality, subtype, anatomical site, severity, acuity, etiology, temporality, etc.). Example: mention 'bilateral cleft palate' -> concept 'Cleft palate' (mention adds 'bilateral').
- EXACT: the mention and the concept denote the SAME level of specificity (synonyms or clinically equivalent). Example: mention 'sepsis' -> concept 'Sepsis'.

Only these two labels are allowed. If the mention is NOT more specific than the concept, label EXACT. First give a one-sentence justification, then the label, via the annotate tool.
```

The `bilateral cleft palate` example above is preserved verbatim because it
was part of the executed prompt. It is independent of the empirical worked
example used in the current manuscript.

## Exact per-item prompt

```text
Clinical mention: {english}
Assigned SNOMED CT concept: {gold_label} (code {gold_code})

Is the mention EXACT or NARROW relative to the concept?
```

## Structured-output schema

```json
{
  "name": "annotate",
  "description": "Record the granularity relation.",
  "input_schema": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "One sentence: does the mention add specificity the concept lacks?"
      },
      "label": {
        "type": "string",
        "enum": ["EXACT", "NARROW"]
      }
    },
    "required": ["reasoning", "label"]
  }
}
```

## Invocation outline

```python
MODEL = host.reasoning_model()

def make_req(row, mt=200):
    return {
        "prompt": make_prompt(row),
        "system": RUBRIC,
        "model": MODEL,
        "tools": [TOOL],
        "tool_choice": {"type": "tool", "name": "annotate"},
        "max_tokens": mt,
    }

all_reqs = [make_req(row) for _, row in df.iterrows()]
for i in range(0, len(all_reqs), 400):
    results.extend(host.llm(all_reqs[i:i + 400], max_concurrency=24))

retry_idx = df.index[df["annotator2_rel"] == "UNPARSED"].tolist()
if retry_idx:
    retry = [make_req(df.loc[ix], mt=500) for ix in retry_idx]
    retry_output = host.llm(retry, max_concurrency=12)
```

## Recorded result

- Automated labels: 545 EXACT, 255 NARROW, 0 unparsed.
- Native-label × automated-label confusion matrix:
  `[[527, 36], [18, 219]]` in EXACT/NARROW row and column order.
- Agreement: 746/800 = 93.25%.
- Cohen's kappa: 0.8416016.
- Private result artifact: `iaa_full.csv`, SHA-256
  `5977a61fe96608e83c0d7e48117a5765dbc34fdff94f995ab887434fab5ab22d`.

The Qwen2.5-32B-Instruct output retained elsewhere in the research archive is
from a later 2,336-item multi-model robustness experiment. It is not the source
of the 800-item kappa reported above.
