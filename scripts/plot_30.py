from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import math

RESULTS = Path("outputs/official_subset/summary_30/official_subset_30_results.csv")
CATS = Path("outputs/official_subset/summary_30/official_subset_30_category_counts.csv")
OUTDIR = Path("outputs/official_subset/summary_30/plots")
OUTDIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RESULTS)
cat_df = pd.read_csv(CATS)

# 类型整理
for col in ["similarity", "milestone_similarity", "turn_count", "no_exception"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# 主类别（取 categories 的第一个标签）
def primary_cat(x: str) -> str:
    if pd.isna(x) or not str(x).strip():
        return "UNKNOWN"
    return str(x).split("|")[0]

df["primary_category"] = df["categories"].apply(primary_cat)

# 1) 总览指标图
metrics = {
    "Avg Similarity": df["similarity"].mean(),
    "Avg Turn Count": df["turn_count"].mean(),
    "No-Exception Ratio": df["no_exception"].mean(),
}
plt.figure(figsize=(7, 4))
plt.bar(metrics.keys(), metrics.values())
plt.ylim(0, max(1.0, math.ceil(max(metrics.values()))))
plt.title("Official ToolSandbox Filtered Subset (30 runs): Overview")
plt.ylabel("Value")
for i, v in enumerate(metrics.values()):
    plt.text(i, v + 0.02, f"{v:.3f}", ha="center")
plt.tight_layout()
plt.savefig(OUTDIR / "01_overview_metrics.png", dpi=200)
plt.close()

# 2) 类别分布图
plt.figure(figsize=(8, 4))
plt.bar(cat_df["category"], cat_df["count"])
plt.title("Category Distribution (30 official filtered scenarios)")
plt.ylabel("Count")
plt.xticks(rotation=30, ha="right")
for i, v in enumerate(cat_df["count"]):
    plt.text(i, v + 0.1, str(v), ha="center")
plt.tight_layout()
plt.savefig(OUTDIR / "02_category_counts.png", dpi=200)
plt.close()

# 3) similarity 直方图
plt.figure(figsize=(7, 4))
plt.hist(df["similarity"].dropna(), bins=10)
plt.title("Similarity Distribution")
plt.xlabel("Similarity")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(OUTDIR / "03_similarity_hist.png", dpi=200)
plt.close()

# 4) similarity 排序图
df_sorted = df.sort_values("similarity", ascending=False).reset_index(drop=True)
plt.figure(figsize=(10, 6))
plt.bar(range(len(df_sorted)), df_sorted["similarity"])
plt.title("Per-Scenario Similarity (sorted)")
plt.xlabel("Scenario Rank")
plt.ylabel("Similarity")
plt.ylim(0, 1.05)
plt.tight_layout()
plt.savefig(OUTDIR / "04_similarity_ranked.png", dpi=200)
plt.close()

# 5) similarity vs turn_count 散点图
plt.figure(figsize=(7, 5))
for cat in sorted(df["primary_category"].dropna().unique()):
    sub = df[df["primary_category"] == cat]
    plt.scatter(sub["turn_count"], sub["similarity"], label=cat)
plt.title("Similarity vs Turn Count")
plt.xlabel("Turn Count")
plt.ylabel("Similarity")
plt.ylim(-0.02, 1.05)
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUTDIR / "05_similarity_vs_turns.png", dpi=200)
plt.close()

# 6) Top-5 / Bottom-5 图
top5 = df.nlargest(5, "similarity")[["name", "similarity"]]
bottom5 = df.nsmallest(5, "similarity")[["name", "similarity"]]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
axes[0].barh(top5["name"], top5["similarity"])
axes[0].set_title("Top 5 Scenarios by Similarity")
axes[0].set_xlim(0, 1.05)

axes[1].barh(bottom5["name"], bottom5["similarity"])
axes[1].set_title("Bottom 5 Scenarios by Similarity")
axes[1].set_xlim(0, 1.05)

plt.tight_layout()
plt.savefig(OUTDIR / "06_top5_bottom5.png", dpi=200)
plt.close()

print(f"plots saved to: {OUTDIR}")