# RCC-8 数据与参考代码来源

本任务使用作者发布的 [STaR 数据集](https://huggingface.co/datasets/erg0dic/STaR/tree/677a34ae27692366ad4c5c9636800e93ca024e73)。数据卡标注 MIT 许可；原始数据卡副本是 `DATASET_README.md`。论文为 [Systematic Relational Reasoning with Epistemic Graph Neural Networks](https://proceedings.iclr.cc/paper_files/paper/2025/file/6590cb829f5ffef50050f3e5845fbb4c-Paper-Conference.pdf)。

当前包采用 `train_rcc8.csv` 和 `test_rcc8_k_{2..9}_b_{1..3}.csv`，共 25 个原始 CSV；具体版本、文件名、行数、SHA-256 与作者仓库 Git blob OID 见 `manifest.json`。文件未重新生成、抽样、去重或改写。测试题为作者公开题目，不能宣称独立未公开 Hidden。

出题方 `workspace/reference/method.py` 适配自作者 [gnn-sg 仓库](https://github.com/erg0dic/gnn-sg)，原代码采用 MIT 许可；许可文本保留在 `LICENSE.code-upstream`。Reference 不进入 Agent 可见的 `harbor_task` 目录。任务中自行实现的 R-GCN 起点不是作者公开仓库提供的 R-GCN 实现。具体适配差异见出题方的 `expert_evidence/PROTOCOL_ALIGNMENT.md`。
