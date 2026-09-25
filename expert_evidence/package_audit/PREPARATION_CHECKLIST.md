# ToB 242 与 Example 的准备项对照

| Example 区块 | 本题状态 | 本题文件 / 决定 |
|---|---|---|
| 顶层说明 | 已准备 | `README.md`，明确只做出题准备 |
| Agent 八章节题面 | 已准备 | `workspace/harbor_task/instruction.md` |
| 任务元信息 | 草案 | `workspace/harbor_task/task.toml`，沿用 Example 教学格式；原生 Harbor schema 待核对 |
| Docker 环境 | 草案 | `environment/Dockerfile`、`requirements.txt`；尚未完成构建与 GPU 验证 |
| 公开资源与来源 | 已准备 | Agent 可见的原始训练 CSV 与清单；评分侧 `evaluation_assets/data/` 的 24 个原始测试 CSV；`DATA_ATTRIBUTION.md` |
| Starter / 初始提交 | 已准备 | R-GCN `environment/starter/method.py` = `solution/method.py` |
| 固定启动脚本 | 已准备 | `solution/solve.sh`；需正式锚点后才能完成评分 |
| 训练、数据、评分、安全 | 设计与代码已准备 | `tests/`，统一协议已固定，未宣称平台安全验收 |
| 无 GPU 合同检查 | 已准备并通过 | `tests/test.sh`，仅检查结构、协议、原始数据哈希 |
| checkpoint 复评入口 | 已准备，未执行 | `tests/rescore_checkpoint.py` |
| 出题方 Reference | 已准备 | `workspace/reference/method.py`，作者 EpiGNN-min 适配 |
| Baseline/Reference 优化证据 | 目录与规范已准备，结果为空 | `optimization_evidence/README.md`；待真实成对试跑 |
| 专家标注与状态 | 草案 | `expert_evidence/expert_annotation.json`、`run_summary.json` |
| Agent 轨迹、最优方法、消融 | 未开始 | 需要真实研究过程，不能预造或复制 Example |
| Hidden 数据 | 不伪造 | 原始论文测试题已经公开；若平台硬性要求未公开题，需另行解决任务要求冲突 |

本阶段的静态检查不会训练模型，也不会计算 benchmark 分数。正式锚点、分差、资源限制和验收结论保持待定。
