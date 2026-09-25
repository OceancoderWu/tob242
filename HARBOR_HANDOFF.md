# ToB 242 Harbor 接入与运行记录

目标版本以本机已安装的 Harbor 0.23.0 为静态核对基准。任务根是 `workspace/harbor_task/`，外层 `tob242/` 含 Reference 与出题证据，不能整体作为 Agent 工作目录。当前独立 Verifier 版 `task.toml` 已由该版本的 `TaskConfig.model_validate_toml` 加载；此前 `shared` 版的 dry-run 不能替代当前版预检。尚未构建 GPU 镜像、运行 Trial 或得到 reward。

## 已接通的路径

| 路径 | 作用 |
|---|---|
| `task.toml` | 原生 `schema_version=1.4`，设置 GPU/CPU/内存、Agent 与 Verifier 时限、独立 Verifier、方法 artifact 及无网络运行 |
| `environment/Dockerfile` | 原生 Docker provider 以 `environment/` 为上下文构建；只复制公开训练 CSV、公开训练器、Starter 与 Agent 题面 |
| `tests/Dockerfile` | 原生 Docker provider 以 `tests/` 为上下文构建独立 Verifier；预置 root 独占测试数据，并复制相同公开训练协议 |
| `/workspace/solution/method.py` | Agent 镜像从 R-GCN Starter 初始化的唯一可改方法文件；仅 Oracle 运行时，私有 `/solution/solve.sh` 会以 Reference 替换它 |
| `/workspace/tests/train_eval.py` | 公开训练/验证入口；`--public-dev` 与 `--smoke` 不读测试数据 |
| `/tests/test.sh` | Harbor Verifier 入口；清理旧 reward，保护测试资产，运行合同检查和正式单 seed grader |
| `/tests/benchmark_data/` | 独立 Verifier 镜像预置的 24 个原始、已公开测试 CSV；构建时即设为仅 root 可读 |
| `/tests/anchors.json` | 仅在真实 B/R 成对证据通过质量门后部署的可信锚点；当前不存在 |
| `/logs/verifier/reward.txt` | grader 从其内存中的正式 score 原子写入的 Harbor 标量结果 |

Harbor 0.23.0 的 `separate` 模式在 Agent 结束后收集 `/workspace/solution/method.py`，并按原路径上传到独立 Verifier 容器。`tests/` 是独立容器的构建上下文，不会进入 Agent 容器；Verifier 镜像构建时把测试 CSV 和锚点设为 root 独占。Verifier 以 root 运行，冻结提交方法的权限；候选训练和推理通过 `runuser` 切换为 `researcher`。root 评分进程只向低权限推理进程传图输入，标签留在评分进程。此隔离仍待目标 Linux GPU 容器用越权读取候选作负例验证；原始题库已公开，不能因此声称“全新隐藏题”。

## 还不能声称通过的事项

1. `optimization_evidence/` 尚无当前 seed 42 协议的 Baseline 与 Reference 训练、模型和独立重载；`tests/anchors.json` 因此缺失，正式 `test.sh` 会明确失败，不会写伪 reward。
2. 本机 macOS 是 aarch64 且磁盘空间有限，未进行 Linux x86_64 CUDA Docker 构建或 GPU 完整试跑；PyG wheel、artifact 转交、权限和 `runuser` 行为需在目标机器验证。已有 GPU 服务器没有 Docker，本轮用户要求只修准备工作，禁止开始实验。
3. `task.toml` 的时限是待实测资源上限；单 seed、24 组推理、12h 容器稳定性和两条 Agent 各10h 有效迭代均需真实日志。单 seed 无法满足教程的 `3σ_B` 随机性证据门槛，需要任务方接受这一偏离。
4. 当前 `separate` 版未运行 dry-run；如果平台实际 Harbor 版本不同于 0.23.0，须在该版本重新执行 schema、构建及 Trial 检查。

## 完成证据后的命令

```bash
cd tob242
PYTHON=/path/to/cuda-python bash expert_evidence/run_pair.sh
harbor run -p workspace/harbor_task -a oracle -e docker -n 1 -o /path/to/jobs
```

第一条将在实验阶段真实运行两次训练及两次独立重载，只在本题单 seed 质量门全部满足时部署锚点。第二条是需要 GPU 的正式 Trial；届时保存同一 Trial 的 `config.json`、`result.json`、`trial.log`、Verifier 输出和 `reward.txt`。本轮没有执行上述命令。
