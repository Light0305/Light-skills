# Synthetic manuscript A — not real research

## User request

请对下面这篇完成稿做投稿前内部评审。尚未选择期刊；目前没有原始数据或运行代码。请直接审已有材料。

## Title

A segmentation method evaluated across three independent sites

## Abstract

We evaluate Method A against Baseline B on three held-out sites. Method A outperforms B at every site. The mean per-image IoU is 0.60, while the mean per-image Dice is 0.72. No significant difference in adverse events was detected (p=0.28), demonstrating equivalent safety.

## Methods

The training, development, and held-out test patients are disjoint. Hyperparameters were selected on the development split. The test set contains 30 patients at each of sites X, Y, and Z, with one image per patient. For each method, IoU and Dice are computed per image and then averaged across test images. The two metrics are averaged separately. Training used three seeds. The main table reports the mean across the three seed-specific site means. The study is exploratory. Safety events are reported without an equivalence margin or equivalence analysis.

## Results

Table 1. Mean test IoU by site. Higher is better.

| Method | X | Y | Z |
|---|---:|---:|---:|
| A | 0.65 | 0.62 | 0.53 |
| B | 0.60 | 0.60 | 0.55 |

Across sites, mean IoU is 0.60 for A. Separately computed mean Dice is 0.72. No raw per-image values or uncertainty estimates are included. The adverse-event comparison yielded p=0.28.

## Discussion

The results suggest a possible improvement in average segmentation performance, with variation by site. The paper contains no figures, only Table 1. The study does not establish clinical effectiveness. Data and code are not included in this review packet; the authors have not yet prepared availability statements. The current author version has no target-journal formatting claims.
