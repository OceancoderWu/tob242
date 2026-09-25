# EpiGNN Reference 来源核查

核查日期：2026-09-26。作者仓库 [erg0dic/gnn-sg](https://github.com/erg0dic/gnn-sg) 固定到 commit `525b9e132aadf76b373e488a9e7e7b255493b6d2`。`upstream/src/model_nbf_fb.py`、`model_nbf_general.py`、`train.py`、`utils.py` 与该 commit 的 GitHub Raw 文件逐字节一致，SHA-256 见 `source_manifest.json`。`fb_model_rcc8.yaml` 也逐字节一致。

`workspace/reference/method.py` 不是凭空重新实现：它合并了作者的 `NBFCluttr`、`NBF_base`、`NBFdistRModule`、`NBFdistR`、关系打分和 margin loss 函数。AST 核对显示这些类和函数的主体与固定的作者源码一致；`NBFdistR.forward` 仅第一条构造 `Batcher` 的语句改为无目标标签的图字典，其后 19 条语句完全相同。外层新增 `Reference`、`build_model` 和 `training_loss` 接口；loss 利用作者的 facet 均值与推理分数之间的代数等价关系。最短路从作者对整批图算 all-pairs Bellman-Ford 改成只对查询源节点计算 single-source Bellman-Ford，保留路径选择。适配记录和边界见 `PROTOCOL_ALIGNMENT.md`。

作者当前仓库中 `model_nbf_fb.py` 引入了 `get_all_source_sink_paths_from_edge_index`，`train.py` 引入了 `get_temp_schedule`，但固定版本的 `utils.py` 均未定义这两个名字。GPU 上先前可运行的镜像仅删除了这两条未使用的 import；模型数学与上述固定源码相同。此处 `upstream/` 保存未改写的官方文件，不能再把 GPU 镜像中的 import 修补版称作官方源码。

先前在 GPU 上做过小样本适配对照：24 组各取 2 题，核对初始化、预测、margin loss 和梯度，结果通过。该检查比较的是可导入的两处 import 修补版与适配版；它不替代完整 benchmark 训练，也不证明所有输入上的位级等价。用户要求本阶段不重跑，故本次只进行源码和配置静态核查。
