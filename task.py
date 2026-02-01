import random
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr, linregress
from dataclasses import dataclass
from typing import Dict, List
random.seed(123)

price = [math.exp(random.gauss(5.5, 0.6)) for _ in range(1000)]
discount = [
    max(0, min(50, 20 - 0.003 * p + random.gauss(0, 2)))
    for p in price
]

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.scatter(price, discount, alpha=0.4)
plt.xlabel("Price")
plt.ylabel("Discount (%)")
plt.title("Price vs Discount")

plt.subplot(1, 2, 2)
plt.hist2d(price, discount, bins=40)
plt.xlabel("Price")
plt.ylabel("Discount (%)")
plt.title("Discount Density")
plt.colorbar()

plt.tight_layout()
plt.show()


df_table = pd.DataFrame([
    {"Product": "A", "Price": 10.0, "Discount": 0.60, "Rating": 4.2},
    {"Product": "B", "Price": 15.0, "Discount": 0.05, "Rating": 2.7},
    {"Product": "C", "Price": 20.0, "Discount": 0.20, "Rating": 2.9},
])

print("\nPRODUCT SUMMARY TABLE")
print(df_table)


np.random.seed(0)

df = pd.DataFrame({
    "subcategory": np.random.choice([f"subcat_{i}" for i in range(1, 21)], 1000),
    "price": np.random.lognormal(3.0, 0.8, 1000),
    "rating": np.clip(np.random.normal(4.0, 0.6, 1000), 1, 5)
})

grp = (
    df.groupby("subcategory", as_index=False)
      .agg(
          avg_price=("price", "mean"),
          avg_rating=("rating", "mean"),
          count=("rating", "size"),
          sd_rating=("rating", "std")
      )
)

plt.figure(figsize=(8, 5))
plt.scatter(
    grp["avg_price"],
    grp["avg_rating"],
    s=grp["count"] / 3,
    alpha=0.6
)
plt.xscale("log")
plt.xlabel("Avg Price (log)")
plt.ylabel("Avg Rating")
plt.title("Avg Price vs Rating by Subcategory")
plt.show()

pr, _ = pearsonr(np.log(grp["avg_price"]), grp["avg_rating"])
sr, _ = spearmanr(grp["avg_price"], grp["avg_rating"])

print(f"\nCorrelation (Pearson log-price): {pr:.3f}")
print(f"Correlation (Spearman): {sr:.3f}")


np.random.seed(42)

df2 = pd.DataFrame({
    "Discount": np.random.uniform(0, 50, 1000)
})
df2["Rating"] = np.clip(
    3 + 0.01 * df2["Discount"] + np.random.normal(0, 1, 1000),
    1, 5
)

corr, p = pearsonr(df2["Discount"], df2["Rating"])
print(f"\nDiscount vs Rating Correlation: {corr:.3f} (p={p:.3f})")

plt.scatter(df2["Discount"], df2["Rating"], alpha=0.4)
plt.xlabel("Discount (%)")
plt.ylabel("Rating")
plt.title("Rating vs Discount")
plt.grid(alpha=0.3)
plt.show()


dates = pd.date_range("2025-01-01", periods=90, freq="D")

df_time = pd.DataFrame({
    "date": dates,
    "discount": np.random.uniform(5, 30, 90)
})

daily = df_time.groupby("date", as_index=False)["discount"].mean()

x = np.arange(len(daily))
slope, intercept, r, _, _ = linregress(x, daily["discount"])

plt.figure(figsize=(10, 4))
plt.plot(daily["date"], daily["discount"], label="Daily Avg")
plt.plot(
    daily["date"],
    slope * x + intercept,
    linestyle="--",
    label=f"Trend (R²={r*r:.2f})"
)
plt.legend()
plt.title("Average Discount Trend")
plt.xlabel("Date")
plt.ylabel("Discount (%)")
plt.show()


class KPIMetrics:
    average_price: float = 950
    average_discount: float = 40
    average_rating: float = 3.8

    def _post_init_(self):
        self.effective_price = self.average_price * (1 - self.average_discount / 100)

kpis = KPIMetrics()

print("\n" + "=" * 60)
print("E-COMMERCE KPI SUMMARY")
print("=" * 60)

print(f"Avg Price        : ${kpis.average_price}")
print(f"Avg Discount     : {kpis.average_discount}%")
print(f"Effective Price  : ${kpis.effective_price:.2f}")
print(f"Avg Rating       : {kpis.average_rating} / 5")

risk = (
    "CRITICAL"
    if kpis.average_discount > 35 and kpis.average_rating < 4
    else "MODERATE"
)

print(f"\nBusiness Risk Level: {risk}")

print("\nRECOMMENDATIONS")
print("1. Reduce discounts to 25–30%")
print("2. Improve product quality & delivery")
print("3. Use targeted / loyalty-based discounts")
print("4. Focus on rating-driven growth")

