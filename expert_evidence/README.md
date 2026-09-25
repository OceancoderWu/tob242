# 出题方材料

该目录保存题目设计依据、正式成对实验脚本与后续真实专家过程。当前已提供：

- `PROTOCOL_ALIGNMENT.md`、`EVAL_AUDIT.md`：论文、作者 Eval 与本任务的逐项对应和冲突记录。
- `SOURCE_PROVENANCE.md`、`BASELINE_LINEAGE.md`、`GPU_VERSION_COMPARISON.md`：Reference 官方源码、GPU 版本关系及 R-GCN 已试跑模型的来源核查。
- `upstream/`、`source_manifest.json`：Reference 适配所用作者代码及文件哈希。
- `check_reference.py`：未来复核适配行为的脚本。
- `preflight.py` 与 `package_audit/static_preflight.json`：只读检查题包、双镜像输入、协议、数据哈希和语法；不训练模型，也不代表平台验收。
- `run_pair.sh`、`package_run.py`、`summarize.py`、`evidence_io.py`：按真实 seed 训练、重载、规范打包、复算质量门并有条件部署锚点。
- `expert_annotation.json`、`run_summary.json`：当前已准备事项与未验收状态，数值锚点为 `null`。
- `package_audit/PREPARATION_CHECKLIST.md`：与 Example 逐项对照的交付清单。
- `专家作业说明文档.md`：未来专家 Agent 研究的任务边界与留证要求。

没有创建 `best_method/`、Agent trajectory 或 post-validation 文件，因为没有真实 Agent 研究过程。Reference 存放于 `workspace/reference/`，它与这些出题者材料都不得进入 Agent 实际工作区。
