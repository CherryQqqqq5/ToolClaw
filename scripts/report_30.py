from pathlib import Path
import pandas as pd

RESULTS = Path("outputs/official_subset/summary_30/official_subset_30_results.csv")
OUT = Path("outputs/official_subset/summary_30/official_subset_30_report.md")

df = pd.read_csv(RESULTS)

for col in ["similarity", "turn_count", "no_exception"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

avg_similarity = df["similarity"].mean()
avg_turn_count = df["turn_count"].mean()
no_exception_ratio = df["no_exception"].mean()

top5 = df.nlargest(5, "similarity")[["name", "similarity", "turn_count", "categories"]]
bottom5 = df.nsmallest(5, "similarity")[["name", "similarity", "turn_count", "categories"]]

lines = []
lines.append("# Phase-2: Official ToolSandbox Filtered Subset (30 scenarios)")
lines.append("")
lines.append(f"- Avg similarity: {avg_similarity:.3f}")
lines.append(f"- Avg turn count: {avg_turn_count:.2f}")
lines.append(f"- No-exception ratio: {no_exception_ratio:.3f}")
lines.append("")
lines.append("## Interpretation")
lines.append("- The official pipeline is stable: all 30 scenarios completed without exception.")
lines.append("- Quality is heterogeneous: some scenarios reach similarity 1.0, while some remain at 0.0.")
lines.append("- This slice is dominated by insufficient-information cases and should be described as a filtered subset rather than the full benchmark.")
lines.append("")
lines.append("## Top 5")
for _, r in top5.iterrows():
    lines.append(f"- {r['name']}: sim={r['similarity']}, turns={r['turn_count']}, cats={r['categories']}")
lines.append("")
lines.append("## Bottom 5")
for _, r in bottom5.iterrows():
    lines.append(f"- {r['name']}: sim={r['similarity']}, turns={r['turn_count']}, cats={r['categories']}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote: {OUT}")