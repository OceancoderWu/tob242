# Baseline 与 Reference 正式训练证据

目前没有正式成对结果。`expert_evidence/run_pair.sh` 在目标 GPU 环境真实运行后，按预先固定的 seed `42` 生成以下结构；不得用旧协议的单 seed 试跑或论文表格补值。

```text
optimization_evidence/
├── README.md
├── 训练证据说明.md
├── baseline_runs/seed_<seed>/
│   ├── result.json                 # 角色、协议、执行、指标、质量门、产物索引
│   ├── run.log                     # 原始 stdout/stderr
│   ├── trainer_result.json         # 共同训练器原始结果
│   └── model/
│       ├── model.pt
│       ├── artifact.json
│       ├── reload.log
│       └── reload_result.json
├── reference_runs/seed_<seed>/     # 同结构
├── comparison_summary.json
└── anchors.json                    # 仅测得的 Baseline 锚点；出题方保管
```

Baseline 与 Reference 的训练/验证行索引、训练预算、数据和测试组完全一致；两种方法各自初始化训练。失败轮标 `INVALID` 并保留原始日志。每轮保存真实 checkpoint 并在独立进程重载复评。`comparison_summary.json` 汇总 seed 42 的成对结果、正向改善和 Reference 归一化 `[0.15,0.8]`。只在这些条件全部满足时，脚本把锚点复制到 Verifier 的 `tests/anchors.json`。单 seed 不产生样本标准差或 `3σ_B` 结论。

全 24 组宏平均是本任务主指标；15 个长链组是诊断指标。论文 Figure 4 的每个 `(k,b)` 原始 accuracy 均需保留，不能只选有利的长度。当前缺失的训练证据和锚点如实保持缺失；README 不是运行证明。
