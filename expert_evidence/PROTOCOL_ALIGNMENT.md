# 与论文 benchmark 的对应关系

论文：Systematic Relational Reasoning with Epistemic Graph Neural Networks，ICLR 2025。本文包锁定论文 Figure 4 的 RCC-8 主实验，不包含论文所有其他任务/消融实验。

- 论文：https://proceedings.iclr.cc/paper_files/paper/2025/file/6590cb829f5ffef50050f3e5845fbb4c-Paper-Conference.pdf
- 作者仓库：https://github.com/erg0dic/gnn-sg
- 原始数据：https://huggingface.co/datasets/erg0dic/STaR/tree/677a34ae27692366ad4c5c9636800e93ca024e73

上游源码固定到 GitHub commit `525b9e132aadf76b373e488a9e7e7b255493b6d2`。逐组 Eval 核查见 `EVAL_AUDIT.md`；R-GCN 试跑代码来源见 `BASELINE_LINEAGE.md`。

## 已固定的对应项

| 项目 | 本包决定 | 证据/性质 |
|---|---|---|
| 预测任务 | 有向关系图 + 有序查询对 → RCC-8 八分类 | 与论文一致 |
| 测试题 | k=2–9 × b=1–3，24 原始 CSV，153,600 题 | 内容哈希锁定，无再生成/去重/抽样 |
| 训练源 | 原始 train_rcc8.csv，57,600 行，k=2–4 | Figure 4 及发布数据；Table 8 的 k=2–3 与之冲突 |
| 训练/验证 | 每 seed 原始行 random_split 80/20 | 作者训练代码；撤销此前自定义去重分组划分 |
| 模型选择 | 最高验证准确率，平局最早 | 作者 train.py；撤销此前 CE 平局规则 |
| epochs/batch/hidden/lr | 40 / 128 / 32 / 0.01 | Table 11 |
| Reference facets | 4 | Table 11；发布 YAML 是 8，正文优先 |
| 优化器 | Adam，无 weight decay | F.5.2；发布 train.py 为 AdamW，正文优先 |
| 传播 | 9 轮；Reference 各轮共享参数 | F.5.2 / 发布模型 |
| Reference loss | margin=1，1 negative，cross-entropy distance | Table 11 / 发布损失函数 |
| Baseline loss | cross entropy | 用户明确允许各自损失 |
| 重复次数 | 1，固定 seed 42 | 用户选择单 seed；论文报告 3 次，本题不能复现其误差区间 |
| 报告 | 每组单次 accuracy；全部 24 组 | 组内指标与 Figure 4 对应，跨运行统计不对应 |

## 必须披露的适配与局限

1. 本包 R-GCN 是常规关系卷积适配，含逆边、查询标记、残差/LayerNorm、查询对读出。作者公开仓库没有提供可确认的同款 R-GCN 基线实现和完整超参，故不能声称它逐项重现论文 R-GCN。共同训练参数与传播范围已固定；不要用论文 R-GCN 分数替代本包实测值。
2. 模型面对的关系顺序固定排序。原代码从 Python set 构造顺序，结果依赖进程 hash 顺序。固定语义映射不改变题目，但会影响给定 seed 的初始随机映射。
3. 训练顺序采用独立 torch.Generator(seed)，让两个模型每 epoch 的样本顺序相同；作者使用全局 RNG，初始化和负采样会影响 shuffle。验证只算 accuracy，不额外采样负例来记损失。不能保证与作者某次运行逐 bit 相同。
4. Reference 保留作者的构造顺序、原始参数和传播数学，只移除 batch 中未使用的目标标签字段，将逐查询 Bellman-Ford 路径计算替换不必要的 all-pairs 计算，并把 margin loss 从 logits 等价表达。此前 GPU 上的小样本检查比较过初始化、预测、损失和梯度；结果文件仍在服务器上，当前目录中没有可复核的 `reference_parity.json`。固定上游 commit 与源码核查见 `SOURCE_PROVENANCE.md`，这不构成全数据训练等价证明。
5. 原始代码构造了许多未使用的模块。总参数量不能用于推断有效容量；每次运行记录首批次有梯度的参数量。不能把 EpiGNN 的全部 1.7M 参数与 R-GCN 活跃参数直接作容量归因。
6. 24 组宏平均是本题评分汇总，15 组长链均值是附加指标。正式对比论文优先看全部 24 个分组，不把归一化 AutoResearch score 当成论文 accuracy。
7. 原始训练/测试数据可能出现相同图输入，短链存在重合。为保持论文题目，不去重、不换题。长链指标单独披露。公开测试可用于研究反馈，不能伪称独立、未公开 Hidden。
8. 要求沿用公开数据，因此无法同时承诺“原题从未公开、无法发现参考方法”。隐藏答案文件、隔离评测进程是工程保护，不会让公开 benchmark 变成新隐藏数据。
9. GPU、软件版本在各运行 provenance 中记录；可运行兼容环境不等于作者机器逐项一致。原作者训练随机序列和依赖锁文件不完整，这些未知项不应填成“完全一致”。

## 验收原则

原始 benchmark 优先，不为制造分差削弱 Baseline，不换测试题，不根据 Reference 分数反推评分上界。当前固定 seed 42；若 Reference 归一化分数不在 [0.15,0.8] 或没有严格优于 Baseline，明确记录不通过。单 seed 不能计算 Baseline 样本标准差，因而不能满足教程的 `3σ_B` 随机性质量门；须由任务方明确接受这一偏离。保持数据与结果，不根据分数改 seed 或评分上界。

正式 10h×2 Agent 研究轨迹和实际 Harbor 平台验证仍需真实运行，不能从模板生成假结果。当前独立 Verifier 版 `task.toml` 已按本机 Harbor 0.23.0 原生 schema 改写并通过静态加载；此前的 `shared` 版曾通过 dry-run，当前版尚未执行。镜像构建、GPU 正式评分及平台隔离尚未完成动态验证。
