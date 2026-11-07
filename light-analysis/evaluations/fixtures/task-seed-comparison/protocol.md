# Task-seed comparison

This is a synthetic validation fixture, not measured research data.

Research question: does proposed method A improve the mean held-out accuracy over baseline B across tasks in the intended application domain? The four available tasks are a convenience sample, not a probability sample of the domain. Task scores receive equal weight. A gain of 0.01 accuracy (one percentage point) was the project's practical relevance threshold before these outputs were generated. The current result file has already been seen by the researcher; no preregistered analysis plan or timestamped plan is available.

Each task has its own fixed train/validation/test split, shared by the two methods. The same evaluation implementation and resource limits were used. Each method was trained three times. Seed labels 1/2/3 are local labels; methods use independent random-number streams and they do not identify matched training realizations. There are no per-test-example predictions in this fixture. Tasks differ in content and difficulty. More training runs on an existing task do not provide additional task identities.

The outputs in scores.csv are complete, with no excluded run. Larger scores are better. All 24 training/evaluation processes completed successfully and all output checks passed. There is no available evidence about a causal mechanism, deployments or additional tasks.

The current authorization covers analysis of existing material and a concrete follow-up brief. New experiment execution is outside this evaluation. Remaining experiment budget has not been set.
