#!/usr/bin/env python3
"""K-Means clustering of drivers (unsupervised, NO prediction) on features produced by the Hadoop jobs."""
import os, sys, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mapreduce"))
from schemas import SCHEMAS
M, OUT, FIG = "results/mapreduce/", "results/analysis/", "figures/"
mr = lambda n: pd.read_csv(M + n + ".tsv", sep="\t", header=None, names=SCHEMAS[n], na_values=[""])
dr = pd.read_csv("data/clean/drivers/drivers.csv")[["driverId", "full_name", "code"]]
j1 = mr("job1_driver_performance"); j4 = mr("job4_qualifying_vs_race"); j4 = j4[j4.rtype == "DRIVER"].copy(); j4["driverId"] = j4.key.astype(int)
d = j1.merge(j4, on="driverId", suffixes=("", "_q")).merge(dr, on="driverId")
d = d[d.entries >= 40].copy()
d["win_rate"] = d.wins / d.entries * 100; d["podium_rate"] = d.podiums / d.entries * 100; d["laps_led_per_race"] = d.laps_led / d.races
F = ["avg_finish_all", "avg_rel_pace_pct", "consistency_cv_pct", "win_rate", "podium_rate", "laps_led_per_race", "avg_qual_pos", "avg_gain_vs_grid"]
X = StandardScaler().fit_transform(d[F])
ks = range(2, 9); inertia, sil = [], []
for k in ks:
    km = KMeans(k, n_init=20, random_state=42).fit(X); inertia.append(km.inertia_); sil.append(silhouette_score(X, km.labels_))
best_k = 3 + int(np.argmax(sil[1:]))   # k=2 (best raw silhouette) only splits front vs midfield; best silhouette among k>=3 used for finer interpretation
print("silhouette:", dict(zip(ks, np.round(sil, 3))), "-> best k =", best_k)
fig, ax = plt.subplots(1, 2, figsize=(11, 4)); ax[0].plot(ks, inertia, "-o", color="#E10600"); ax[0].set_title("Elbow method (inertia)"); ax[0].set_xlabel("k")
ax[1].plot(ks, sil, "-o", color="#2F6FDE"); ax[1].axvline(best_k, ls="--", color="grey"); ax[1].set_title("Silhouette score"); ax[1].set_xlabel("k")
fig.tight_layout(); fig.savefig(FIG + "11_kmeans_elbow_silhouette.png", dpi=150); plt.close(fig)
km = KMeans(best_k, n_init=50, random_state=42).fit(X); d["cluster"] = km.labels_
prof = d.groupby("cluster")[F].mean(); prof["n_drivers"] = d.groupby("cluster").size()
order = prof.avg_finish_all.sort_values().index.tolist(); remap = {c: i + 1 for i, c in enumerate(order)}
d["cluster"] = d.cluster.map(remap); prof = d.groupby("cluster")[F].mean(); prof["n_drivers"] = d.groupby("cluster").size()
prof["members"] = d.groupby("cluster").code.apply(lambda s: ", ".join(sorted(s)))
prof.round(2).to_csv(OUT + "kmeans_cluster_profiles.csv"); d[["full_name", "code", "cluster"] + F].round(3).sort_values(["cluster", "avg_finish_all"]).to_csv(OUT + "kmeans_driver_clusters.csv", index=False)
P = PCA(2, random_state=1).fit(X); Z = P.transform(X)
cols = ["#E10600", "#FF8000", "#2F6FDE", "#9a9aa5", "#27F4D2", "#6C7FD8", "#52C41A", "#222222"]
fig, ax = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.1, 1]})
for c in sorted(d.cluster.unique()):
    m = (d.cluster == c).values; ax[0].scatter(Z[m, 0], Z[m, 1], s=90, c=cols[c - 1], label=f"Cluster {c} (n={m.sum()})", edgecolor="white")
for i, (_, r) in enumerate(d.iterrows()): ax[0].annotate(r.code, (Z[i, 0], Z[i, 1]), fontsize=7.5, xytext=(4, 4), textcoords="offset points")
ax[0].set_xlabel(f"PC1 ({P.explained_variance_ratio_[0]*100:.0f}% var)"); ax[0].set_ylabel(f"PC2 ({P.explained_variance_ratio_[1]*100:.0f}% var)")
ax[0].set_title(f"K-Means driver clusters (k={best_k}), PCA projection"); ax[0].legend()
z = (prof[F] - d[F].mean()) / d[F].std(); im = ax[1].imshow(z.values, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto"); ax[1].grid(False)
ax[1].set_xticks(range(len(F))); ax[1].set_xticklabels(F, rotation=40, ha="right", fontsize=8); ax[1].set_yticks(range(len(z))); ax[1].set_yticklabels([f"Cluster {i}" for i in z.index])
for i in range(z.shape[0]):
    for j in range(z.shape[1]): ax[1].text(j, i, f"{prof[F].values[i, j]:.1f}", ha="center", va="center", fontsize=7.5)
ax[1].set_title("Cluster profile (colour = z-score; text = mean; red = higher)"); fig.tight_layout(); fig.savefig(FIG + "12_kmeans_clusters.png", dpi=150); plt.close(fig)
json.dump({"k": best_k, "silhouette": dict(zip(map(int, ks), map(float, sil))), "features": F, "n_drivers": int(len(d))}, open(OUT + "kmeans_summary.json", "w"), indent=1)
pd.set_option("display.width", 250); print(prof.round(2).drop(columns="members")); print(prof.members.to_string())
