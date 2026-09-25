# 本地 Reference 与 GPU 服务器版本的关系

只读核查日期：2026-09-26。没有启动训练或测试。

| 对象 | SHA-256 | 关系 |
|---|---|---|
| 本地 `tob242/workspace/reference/method.py` | `69495b0e8015c501a19e54ff61dd29a026138111be695a4d2d2c7cedb9714e09` | AutoResearch 接口适配版 |
| GPU `/root/autodl-tmp/autore/paper242/tob242/workspace/reference/method.py` | 同上 | **逐字节相同**，之前从本地上传 |
| GPU `/root/autodl-tmp/autore/src/gnn-sg-runtime/src/model_nbf_fb.py` | `e1a0f632d3258fa85709ddfae7662050729fa18e292d24c49987e035c1f85fae` | 旧试跑使用的作者模型模块，删去一条不存在且未使用的 import 才可加载 |
| 作者 GitHub commit `525b9e132aadf76b373e488a9e7e7b255493b6d2` 的 `src/model_nbf_fb.py` | `c8679d4b8c700802f982bc835434869070bd88a3941fcbe57c16dc9d093af824` | 未修改的官方文件，保存在本地 `expert_evidence/upstream/` |

GPU 旧试跑 `experiment/rgcn_pair_v1/epignn-seed42` 的 `config.json` 记录：EpiGNN-min、hidden 32、9 轮、4 facets、前后向、min 聚合、Adam lr 0.01、40 epochs、训练 batch 128。旧脚本直接导入 GPU 的 `src/gnn-sg-runtime/src/model_nbf_fb.py`，然后通过 PyG/HeteroData batch 训练；它**没有**导入本地的 `workspace/reference/method.py`。旧试跑曾完整训练并写下结果，不能因此说当前适配版已经按新协议完整训练。

当前 Reference 从同一作者模型核心适配：模型主体、初始化与打分函数静态 AST 与官方源码对应；容器输入改为无目标标签的图字典，最短路从 all-pairs Bellman-Ford 改成只算查询源节点，margin loss 用推理 logits 的等价表达。此前 GPU 小样本检查（24 组各 2 题）比较了两版的初始化、预测、损失和梯度，结果通过。适配差异见 `SOURCE_PROVENANCE.md`。

**训练协议也发生了有意调整：** 旧试跑用按重复图分组去重的 42,789/14,811 训练/验证划分、验证准确率平局再比较交叉熵、测试 batch 64；准备中的论文协议采用原始行 46,080/11,520 划分、平局取最早、测试 batch 128。旧分数和 checkpoint 不作为新任务的正式锚点。
