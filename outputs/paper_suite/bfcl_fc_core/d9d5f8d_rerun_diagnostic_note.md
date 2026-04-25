# BFCL fc_core d9d5f8d Full Rerun Diagnostic Note

## Provenance

- Suite: `bfcl_fc_core`
- Commit: `d9d5f8dc4bfb027022ab8c05ebe23df0f03c2402`
- Command: `PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core`
- Canonical output root: `outputs/paper_suite/bfcl_fc_core`

## Claim Status

This rerun remains **Case D**. BFCL stays a limitation/unsupported evidence source for planner-binding claims.

- `a2_wrong_func_name_le_a0=true`
- `a2_tool_selection_ge_a0=true`
- `a2_success_ge_a0=false`
- `a2_missing_required_lt_a0=false`
- `baseline_missing_required_slice_ready=false`

No claim matrix upgrade is supported by this bundle. `planner_binding_headline` remains a limitation, `bfcl_exact_function_guard` remains pending/unsupported, and `bfcl_missing_required_guarded_reduction` remains unsupported.

## A2 Planner Metrics

| Metric | Prior baseline | d9d5f8d rerun | Interpretation |
| --- | ---: | ---: | --- |
| `bfcl_abstain_candidate_elision` | 776 | 601 | Improved: serial false-abstain repair forced more positive calls. |
| `wrong_call_count_zero_emitted` | 524 | 524 | Not improved: selected-correct rows still fail after schema selection. |
| `wrong_call_count_missing_calls` | 569 | 569 | Not improved: missing-call cardinality remains. |
| `parallel_expected_but_serial_emitted` | 41 | 41 | Not improved: parallel shape preservation still incomplete. |
| `selected_correct_arg_or_shape_error` | 789 | 870 | Regressed in count because more rows reach selected-correct evaluation. |
| `selected_correct_success` | 60 | 154 | Improved: forced serial calls recover additional successes. |

Official snapshot:

- `a0_baseline` success: `0.2803542297832673`
- `a2_planner` success: `0.27476112794220464`
- `a0_baseline` tool selection: `0.48109415054765786`
- `a2_planner` tool selection: `0.4823953235454051`
- `a0_baseline` wrong function bucket: `81`
- `a2_planner` wrong function bucket: `81`

## Diagnosis

The serial abstain repair helped, but it did not solve the primary blocker. The run now shows controlled wrong-function regression and slightly better tool-selection correctness than baseline, but success still trails baseline.

The remaining blocker is post-selection call emission/canonicalization, not candidate coverage, planner override, or ranker weighting:

- Serial rows still produce zero emitted calls after schema selection.
- Non-live parallel rows still lose clause calls or collapse shape.
- Argument value and missing-required failures are secondary until call cardinality and parallel shape are fixed.

## Representative Traces

The repository includes a small trace subset under `representative_traces/` instead of the full trace directory.

| Trace | Why included |
| --- | --- |
| `representative_traces/a2_live_serial_abstain_failure_live_relevance_5-5-0.json` | Live serial abstain failure with schema top-1 available; illustrates remaining false no-call behavior. |
| `representative_traces/a2_non_live_serial_callshape_failure_irrelevance_10.json` | Non-live serial selected-correct failure; illustrates post-selection call-shape/canonicalization failure. |
| `representative_traces/a2_non_live_parallel_shape_failure_parallel_2.json` | Non-live parallel selected-correct failure with wrong count; illustrates remaining parallel clause expansion problem. |
| `representative_traces/a2_live_serial_forced_success_live_irrelevance_10-1-0.json` | Positive control showing the serial force-call path can recover an official success. |

## Next Repair Target

Do not tune planner override, candidate pool preservation, or schema-ranker weights next. The next patch should target BFCL-specific call emission after schema selection:

1. Serial selected-correct rows must materialize exactly one emitted call when schema top-1 is viable.
2. Non-live parallel rows must emit clause-level calls rather than zero-emitting or serializing away parallel structure.
3. Only after call cardinality/shape is repaired should argument value normalization and required-argument grounding become primary.
