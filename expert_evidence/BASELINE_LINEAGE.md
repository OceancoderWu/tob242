# R-GCN 起点的来源

`workspace/harbor_task/solution/method.py` 就是用户此前在 GPU 服务器试跑过的 `results/rgcn_pair_v1/model.py` 的模型结构。不是另起炉灶：九层 `FastRGCNConv`、正反向 16 种关系、查询起终点标记、残差和 LayerNorm、四项查询节点读出及交叉熵均沿用。`audit_rgcn_lineage.py` 静态核对该模型源码，只允许两类差异：将旧 PyG/HeteroData 的取字段方式换成无标签图字典，新增 AutoResearch 所需的 `build_model` 与 `training_loss` 接口。`environment/starter/method.py` 是同一初始源码副本。

此前单 seed 试跑的结果在 `results/rgcn_pair_v1/rgcn-seed42/`：训练完成 40 epochs、24 组测试，见其 `result.json`。该次试跑使用自定义去重分组训练/验证划分（42,789 / 14,811）、验证准确率平局按较低交叉熵选择 checkpoint，并以 15 个长链组为主汇总。这些选择不同于当前按论文作者训练脚本设计的 80/20 原始行划分和严格准确率选点，因此旧 checkpoint、旧分数不能当作当前任务的正式 Baseline 锚点。保留它们作为模型起点确实曾成功训练的证据。

论文对 R-GCN 给出模型类别和结果，但作者公开的 `gnn-sg` 仓库没有可核对为 Figure 4 同款的 R-GCN 实现/完整训练配置。本模型是用户此前批准并试跑的 R-GCN 基线，不能声称逐项复刻论文作者的 R-GCN 数值。
