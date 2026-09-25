# 关系图上的跨长度泛化

## 1. 目标

改进一个可训练的关系图分类模型：用短推理链样本训练，在作者发布的 RCC-8 benchmark 原始测试题上提高关系分类准确率。提交 `solution/method.py`，评测器从头训练并评分。起点是可运行的 R-GCN。

## 2. 任务背景与数据

每条样本给出带关系标签的有向图及一个有序查询节点对，预测该节点对之间的 RCC-8 空间关系。类别顺序固定为 `DC, EC, EQ, NTPP, NTPPI, PO, TPP, TPPI`。这些关系分别表示不连通、外部接触、相等、非相切真包含及其逆关系、部分重叠、相切真包含及其逆关系。图中的边关系是输入，查询关系是答案。节点编号仅标识节点。

数据是 STaR 作者发布的原始 CSV；来源及版本见 `environment/public_assets/manifest.json`。Agent 工作区只挂载训练 CSV；原始测试 CSV 由评分侧读取，测试标签不作为模型输入。不生成新图、不改写答案、不筛掉题目。

- 训练源文件：`train_rcc8.csv`，57,600 条，链长 k=2–4、路径数 b=1–3。
- 每个 seed 使用 PyTorch `random_split` 按原始行划分 80% 训练、20% 验证（46,080 / 11,520），不做去重。
- 测试：`test_rcc8_k_{k}_b_{b}.csv`，k=2–9、b=1–3，共 24 文件，每文件 6,400 题，共 153,600 题。
- 这些是已公开的论文测试题，不构成新的未公开 Hidden 数据。测试标签只能用于评测；训练损失、调参时的 checkpoint 选择只能使用训练/验证划分。

训练分布内的 k=2–4 和分布外的 k=5–9 都必须报告。不得仅测试表现较好的长度或路径数。

## 3. 指标与评分

每个 seed 对每个测试文件计算 accuracy，完整报告 24 组。每组报告 3 个 seed 的均值与 2σ（此包使用总体标准差，另报告总体主指标的样本标准差）。额外报告 k=5–9 的 15 组平均准确率。

本 AutoResearch 包以全部 24 组的宏平均再对 3 个 seed 平均作为 A；论文 Figure 4 逐组结果仍是对照的首要依据。标量汇总和以下归一化是任务评分约定，不是论文中的新实验设置。

`score = (A - B) / (1 - B)`

B 必须来自相同协议下实测 R-GCN 的三 seed 均值。分数不裁剪：低于 Baseline 可以为负；不使用 Reference 分数设置上限。可信 `anchors.json` 未生成时正式评分拒绝运行。

## 4. 可修改范围与接口

只修改 `solution/method.py`。可以修改模型结构、消息计算、关系表示、聚合、查询读出和训练损失；优化器、学习率、训练预算、数据与选择规则固定。

提供两个函数：

```python
def build_model(num_relations=8, num_steps=9):
    # 返回 torch.nn.Module
    ...

def training_loss(logits, targets):
    # 返回有限的标量 Tensor；只在训练时调用
    ...
```

`model(graph)` 返回 `[B, 8]` 有限 logits，越大表示越可能。graph 是仅含输入的字典：

| 字段 | 类型与含义 |
|---|---|
| edge_index | int64 `[2,E]`，合并批次后的有向边 |
| edge_type | int64 `[E]`，关系类别 0–7 |
| query_index | int64 `[2,B]`，有序查询节点对 |
| batch | int64 `[N]`，每个节点所属样本 |
| num_nodes | Python int，总节点数 N |

标签是训练器独立保存的 `[B]` int64 张量，只交给 `training_loss`；不能通过模型输入读取。图张量已放到 GPU。只能使用 PyTorch、PyG、torch-scatter、NetworkX、typing 和 math，禁止外部模型或预训练权重。模型参数总量不超过 2,000,000（包括构造但未使用的参数）。传播迭代预算为传入的 `num_steps=9`，不得私自增加轮数。

## 5. 硬边界与统一实验参数

- seeds 固定 42、43、44；每个 seed 两种方法的训练/验证行索引相同。
- 40 epochs，batch size 128，Adam，learning rate 0.01，weight decay 0，无 scheduler，无梯度裁剪，float32。
- 起点 hidden dimension 32，9 轮传播；本题固定表示宽度 32，模型不得通过增加宽度突破这一约束。
- checkpoint 仅由验证准确率严格提高时更新，平局保留最早 epoch。不得根据测试表现选 checkpoint、seed 或训练轮数。
- 主训练过程每 seed 完成后才评测全部测试文件；不允许把测试题加入训练，或将答案、关系组合表、逐题结果硬编码到实现中。
- 每个 seed 独立初始化；禁止跨 seed 缓存权重和跨评测复用已训练权重。
- 不修改训练器、评分器、入口脚本、数据、协议或锚点。不得访问文件、网络、环境变量或启动外部进程。
- 部署资源暂定：1 张 24 GiB CUDA GPU、8 CPU、16 GiB RAM；单 seed 子进程上限 7,200 秒，完整三 seed 上限 21,600 秒。以上数值尚未完成正式试跑核定，发布前必须据实测冻结。

## 6. 提交要求

仅提交 `solution/method.py`。`solution/solve.sh` 固定，调用共同评测器；checkpoint 和日志由评测器创建。模型输出不可依赖测试标签或数据文件名。

完整评测示例（输出目录必须不存在）：

```bash
bash solution/solve.sh output/run001 /opt/benchmark/anchors.json
```

## 7. 迭代流程

先做接口 smoke test，再完整训练评测；smoke 结果不是 benchmark 分数。可用验证集检查改动，公开测试反馈只用于研究迭代，不能用于训练或选择训练中间的 checkpoint。

```bash
python tests/train_eval.py --method solution/method.py --seed 42 --smoke --output output/smoke001
# 此命令需由评分环境挂载 /opt/benchmark/data；本地出题检查使用 --test-data ../../evaluation_assets/data
```

与 Baseline 比较时使用完整三 seed 协议，检查 24 组结果，不能只报告有利的单 seed。部署必须用容器隔离并强制资源限制；静态检查只是辅助。

## 8. 完成条件

方法可以从头训练，在全部 24 组原始测试题上产生有限 logits，提交通过接口/边界检查；完整三 seed 评测生成 `metrics.json`。研究结果应优于 Baseline，且逐组报告不能隐藏退化。任务包正式发布还需出题者完成锚点、Reference 收益区间、容器和研究轨迹验收；这些不是 Agent 可以修改的目标。
