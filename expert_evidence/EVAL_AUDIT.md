# RCC-8 Eval 与论文/作者代码核对

核查目标是论文 Figure 4 的 RCC-8 benchmark。依据是[论文 PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/6590cb829f5ffef50050f3e5845fbb4c-Paper-Conference.pdf)及作者 [gnn-sg commit 525b9e1](https://github.com/erg0dic/gnn-sg/tree/525b9e132aadf76b373e488a9e7e7b255493b6d2)。本文件为出题准备阶段的源码/数据核查，不声称已做新的完整 GPU benchmark。

| 核查项 | 作者论文/代码 | ToB 242 | 结论 |
|---|---|---|---|
| 题目 | 有向关系图、已知边关系、有序查询边、RCC-8 八类标签 | `tests/data.py` 从原始 CSV 读取同四列，查询关系只交损失/评测 | 题目相同 |
| 数据 | 论文 Figure 4：k=2–9、b=1–3；每组 6,400，共 153,600 | 固定原始 24 CSV；SHA-256 与官方 Git blob OID 记录在 manifest | 测试题相同 |
| 作者脚本额外组 | `get_test_metrics` 循环 k=2–10、b=1–3 | 以论文 Figure 4 / Table 8 的 2–9 为准，k=10 不入论文主图对照 | 明示范围差异；不是漏掉论文 Figure 4 的组 |
| CSV 预处理 | `utils.load_rcc8_file_as_dict` 对 `edges`、`edge_labels`、`query_edge` 用 `ast.literal_eval`，按文件行序读取 `query_label` | `tests/data.read_rows` 相同字段、相同行序、无题目删改 | 解析规则对应；标签 ID 固定为一致的八类排序，作者用 set 顺序 |
| 图输入 | 作者 `ClutrrDataset`/`make_geo_transform` 将 edge index、edge type、query pair 放入 PyG batch，模型计算时使用这些输入 | `tests/data.collate` 合并图并添加节点 offset，保留边方向、关系和查询顺序；标签另存 | 图语义对应，容器形式不同 |
| 预测 | `NBFdistR(..., use_margin_loss=True, infer=True, score_fn='xent', outs_as_left_arg=False)` | Reference wrapper 调用相同参数；小样本对照过预测/loss/梯度 | 算法调用对应，未做全量等价证明 |
| 组内准确率 | `utils.get_acc`: `argmax(axis=1)` 与目标标签逐项比较，再除以样本数；`train.get_batched_test_out` 对 batch 按样本数加权 | `tests/train_eval.evaluate` 逐 batch 计正确题数，除以该文件总题数 | 数学上完全同一组内 accuracy |
| 测试 batch | 作者配置 128，`DataLoader(..., shuffle=True)` | 固定 128，按原文件顺序迭代 | 准确率对样本顺序不敏感；不承诺浮点逐 bit 一致 |
| checkpoint 选择 | 验证准确率严格提高才更新，平局留最早 epoch | `train_eval.py` 同规则；本包从 1 计 epoch，作者从 0 计 | 选择准则对应 |
| 重复和报告 | Figure 4 为 3 次运行的逐 k/b accuracy 曲线及 2σ 区间 | 固定 seed 42，24 组逐组报告单次 accuracy | 测试题和组内 accuracy 对应，但重复次数及 2σ 报告不再与论文一致 |
| 标量分数 | 论文 Figure 4 没有 `(A-B)/(1-B)` | AutoResearch 额外用 24 组宏平均和实测 R-GCN 锚点生成 score | **这是题目平台评分约定，不能称论文原 Eval 指标** |

**结论：** 原始题目、每个 `(k,b)` 的 accuracy 定义、验证选点规则与论文 Figure 4 对齐。数据容器、类别 ID 顺序、测试样本顺序、随机序列和额外的 AutoResearch 标量汇总不是作者逐 bit 的执行方式。论文正文与作者当前配置的 facets、优化器存在冲突，见 `PROTOCOL_ALIGNMENT.md`。因此可以声称“同一论文 benchmark 的逐组评测”，不能声称“论文原代码原环境逐 bit 复现”或把平台 score 当作论文 accuracy。

当前只完成源码、协议、文件哈希和小样本 Reference 适配核查。当前单 seed 协议的完整训练、全量 checkpoint 重载与论文数值对照需要后续明确进入试跑阶段；单次结果不能复现论文的三次均值与误差区间。
