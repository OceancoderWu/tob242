# ToB 242 RCC-8 AutoResearch 任务包

本包使用作者发布的原始训练 CSV 和 Figure 4 对应的 24 组 RCC-8 测试 CSV。Agent 改进 `/workspace/solution/method.py` 中的图关系推理方法；训练和评分协议由任务固定。论文逐组 accuracy 与本题测试题一致；全 24 组宏平均和归一化 `score=(A-B)/(1-B)` 是 AutoResearch 新增的标量合同。Baseline 是查询感知 R-GCN 适配，Reference 是作者 EpiGNN-min 适配，二者并非论文代码逐 bit 复现。

## 当前状态

评分代码、公开验证入口和 Harbor 0.23.0 配置已完成静态接线，**正式投放仍待真实 GPU 证据**。正式协议现为固定 seed 42；`optimization_evidence/` 当前没有该协议的 Baseline/Reference 成对结果、checkpoint 和测得的锚点。`tests/anchors.json` 只有通过正式证据质量门后才由 `expert_evidence/summarize.py` 生成。两条 Agent 轨迹也未开展。不要把当前包或历史单 seed 试跑标成验收通过。

本轮仅修准备工作，未启动任何实验。逐项静态结果见 `expert_evidence/package_audit/static_preflight.json`，修复与待实验项见 `expert_evidence/package_audit/PREPARATION_REVIEW.md`。

## 目录边界

- `workspace/harbor_task/`：交给 Harbor 的任务根。Agent 镜像从 `environment/` 构建，包含公开训练 CSV、只读公开训练器和 R-GCN 起点。
- `workspace/harbor_task/solution/`：仅 Harbor Oracle 调用的私有 Reference 方法与无参入口；常规 Agent 镜像中的 `/workspace/solution/method.py` 仍从 R-GCN Starter 初始化。
- `workspace/harbor_task/tests/benchmark_data/`：原始 24 个公开测试 CSV 的 Verifier 侧副本。Harbor 从 `tests/Dockerfile` 构建独立评分镜像；测试目录在镜像构建时即设为 root 独占，候选训练与推理以 `researcher` 运行，测试标签只在 root 评分进程中使用。
- `workspace/harbor_task/tests/hidden_assets/`：交付时为空。原始论文测试题已公开，本题不声称另有未公开 Hidden。
- `workspace/reference/`：出题方私有 Reference，不在 Agent 构建上下文。
- `optimization_evidence/`：全部正式 Baseline/Reference seed 的训练、模型、重载和统计材料。
- `expert_evidence/`：来源审计、协议说明、出题记录及未来两条 Agent 轨迹。

## 本地与 Harbor 检查

本机已用 Harbor 0.23.0 的 `TaskConfig.model_validate_toml` 加载当前 `task.toml`；旧 `shared` 配置曾通过 dry-run，但不能作为当前独立 Verifier 配置的运行证据。目标环境是 Linux x86_64、CUDA 11.8 兼容 GPU。原生 Docker provider 分别以 `environment/` 和 `tests/` 为 Agent、Verifier 构建上下文：

```bash
docker build --platform linux/amd64 -t tob242-rcc8:0.2 -f workspace/harbor_task/environment/Dockerfile workspace/harbor_task/environment
docker build --platform linux/amd64 -t tob242-rcc8-verifier:0.2 -f workspace/harbor_task/tests/Dockerfile workspace/harbor_task/tests
```

公开迭代在 Agent 容器中运行，不需测试文件与锚点：

```bash
bash /workspace/solution/solve.sh /workspace/output/dev42 42
python /workspace/tests/train_eval.py --method /workspace/solution/method.py --seed 42 --smoke --output /workspace/output/smoke42
```

正式 Harbor Verifier 在独立容器运行 `/tests/test.sh`。Harbor 只转交 Agent 最终的 `/workspace/solution/method.py` artifact；Verifier 固定该文件权限，再用 root 读取测试数据，按固定 seed 42 从头训练候选并经低权限推理进程取得预测，最后原子写 `/logs/verifier/reward.txt`。所有测试文件会校验 SHA-256；模型代码和测试标签不在同一进程。公开题库本身可能被外部获得，这一运行隔离不能改变原始数据的公开性质。

## 正式证据生成

在有 GPU 的受控环境、与任务相同的软件和数据版本下运行：

```bash
cd tob242
PYTHON=/path/to/python bash expert_evidence/run_pair.sh
```

脚本以 seed 42 分别从头训练 Baseline 和 Reference，独立重载，对齐数据划分并生成规范 `result.json`、日志、`model/`。`summarize.py` 复算单次主指标、改善和归一化 Reference 分数。仅当两次训练完整、Reference 严格优于 Baseline 且归一化分数处于 `[0.15,0.8]` 时，才部署测得的 `tests/anchors.json`。单 seed 无法估计随机波动，也不能满足原教程的 `3σ_B` 证据要求；失败结果保留，不能换 seed 或调上界制造通过。

锚点生成后，还需实测 Docker 构建、GPU 完整评分、Harbor Trial、资源/时长、容器 12 小时稳定性和两条各至少 10 小时有效研究轨迹。最终状态以 `expert_evidence/run_summary.json` 和真实运行材料为准。
