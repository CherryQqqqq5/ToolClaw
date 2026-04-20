# Tau-Bench Semantic Audit

This audit decides whether the current `tau-bench` integration is safe to promote into the paper headline benchmark path.

## Verdict

- `promote_tau_bench`: `false`
- current paper role: supporting-only

## Findings

1. `scripts/prepare_tau_bench_source.py` converts upstream task definitions into instruction-only rows and keeps only a reduced subset of metadata.
2. `TauBenchAdapter` scores traces with ToolClaw-specific proxy metrics such as `rule_following`, `interaction_quality`, `tool_efficiency`, and `repair_overhead`.
3. The current pipeline is useful for internal and supporting evidence, but it is not a faithful enough preservation of upstream `tau-bench` semantics to support a headline claim.

## Supporting-Only Metrics

- `mean_success_rate`
- `pass_at_k`
- `consistency`
- `rule_following`
- `interaction_quality`
- `tool_efficiency`
- `repair_overhead`

## Must-Fix Items Before Promotion

1. Preserve more upstream environment and domain-rule semantics in the aligned source.
2. Replace or supplement the current proxy scoring path with a more faithful upstream-compatible evaluation path.
3. Re-run the audit after the adapter, source prep, and scorer are upgraded.
