# Baseline / Reference 训练证据位置

该目录仿照 `example/optimization_evidence/` 预留。本次任务只做出题准备，不运行 benchmark，因此**当前没有正式结果、锚点、checkpoint 或成对比较**；空目录不代表零分或失败。之前被停止的 GPU 部分试跑不纳入正式证据。

未来经明确进入试跑阶段后，每个方法分别记录 seed 42、43、44 三次从头训练：

```text
optimization_evidence/
├── README.md
├── baseline_runs/seed_42 ... seed_44/
├── reference_runs/seed_42 ... seed_44/
├── comparison_summary.json
└── anchors.json
```

每个完整 run 至少保存冻结配置与方法/数据哈希、原始逐 epoch 日志、训练/验证行索引、最佳 checkpoint、验证和 24 个测试组的准确率、峰值显存、耗时、独立进程重载复测。比较只能使用同 seed、同数据行划分、同训练预算的完整运行。缺失值如实标 `null`，不能复制 Example 的分数或论文分数。

全 24 组宏平均和长链 15 组平均都报告；后者是论文关注的分布外诊断，前者用于此任务的 AutoResearch 标量 score。每组按论文形式报告三次均值和 2σ。若 Reference 未稳定优于 Baseline，原样记录并重新审视题目设计，不能减少测试题或调低 Baseline 预算制造差距。
