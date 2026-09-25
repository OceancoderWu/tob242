# ToB 242 准备工作复核

本轮按用户要求只修文件与静态接线，**没有启动模型训练、smoke、评分、Docker 构建、Harbor Trial 或 Agent 研究**。此前的 `qa-reviews/tob242-2026-09-26/` 是修复前报告，不能当成当前版本结论。

## 已修复的准备项

| 范围 | 当前文件和边界 |
|---|---|
| Agent 起点与 Oracle | `environment/starter/method.py` 是 R-GCN；Agent 镜像将它复制到 `/workspace/solution/method.py`。任务根 `solution/method.py` 是与 `workspace/reference/method.py` 相同的私有 Reference，只在 Harbor Oracle 运行时上传。`solve.sh` 无参数可调用。 |
| Harbor 配置 | `task.toml` 按本机 Harbor 0.23.0 的 schema 声明 1 GPU、无网络、独立 Verifier 和唯一方法 artifact；`TaskConfig` 加载、`Task.is_valid_dir` 静态检查通过。 |
| 两套构建上下文 | Agent 从 `environment/Dockerfile` 构建，只有公开训练 CSV、Starter、题面和公开验证工具；独立 Verifier 从 `tests/Dockerfile` 构建，包含原始 24 组测试 CSV、可信代码、相同公开训练协议。两套 COPY 来源均在各自上下文内。 |
| 测试隔离 | 测试 CSV 在 Verifier 镜像构建时设为 root 独占，Agent 容器没有这些文件。Verifier 仅接收方法 artifact，固定其权限；候选训练和推理由普通用户进程执行，root 进程单独读取标签与计算分数。静态 AST 检查是补充，不被当成完整 Python 沙箱。 |
| Public/Dev | `solution/solve.sh` 和 `tests/train_eval.py --public-dev` 只使用公开训练 CSV 的训练、验证划分；无需锚点与测试文件。Agent 日常迭代可只跑一个 seed。 |
| 正式评分 | `/tests/test.sh` 接通合同检查、固定 seed 42 grader、24 组宏平均、归一化 score 和原子 reward；先清理旧的 txt/json reward。失败时不能留下旧分数。 |
| 证据模板 | `expert_evidence/run_pair.sh`、`package_run.py`、`summarize.py` 能按冻结协议记录 Baseline/Reference 的逐 seed 训练、重载、模型哈希与统计；没有真实结果时不生成正式锚点。 |
| 数据与镜像一致性 | `preflight.py` 只读检查训练/测试 CSV SHA-256、两套公开资产镜像、题面和脚本副本、Python 语法、Docker COPY 来源。具体逐项结果见 `static_preflight.json`。 |

单 seed 版本的只读静态复核：`preflight.py` 的 105 项检查全部通过，结果见 `static_preflight.json`；`test_contract.py` 的 3 项文件/协议检查通过；Harbor 0.23.0 的 `TaskConfig.model_validate_toml` 与 `Task.is_valid_dir` 通过。这些检查不构建镜像，也不证明实际运行成功。

## 仍需实验阶段的真实证据

1. 在 Linux CUDA 容器构建两套镜像，核对依赖安装、artifact 转交、`runuser`、文件权限及拒绝越权读取的负例。
2. 真实执行一次 Public/Dev，再完成固定 seed 42 的 Baseline/Reference 成对训练、独立重载和全 24 组评分；据此确认 Baseline 公平、Reference 分数落在 `[0.15,0.8]` 且严格优于 Baseline。当前 `anchors.json` 不存在。单 seed 无法提供教程要求的 `3σ_B` 证据，任务方需接受这一偏离。
3. 在冻结任务上完成两条各至少 10 小时的独立 Agent 研究轨迹、最佳方法复评，以及真实 Harbor Trial、资源/时限和 12 小时稳定性检查。

这三个部分均受本轮“禁止开始任何实验”的指令约束，保持未运行状态。当前版本只能称为**静态准备完成，正式投放未验收**。原始论文测试题已经公开；进程隔离不等于新建未公开 Hidden。旧单 seed 试跑采用另一协议，不作为本题锚点。
