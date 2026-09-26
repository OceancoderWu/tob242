# ToB 242 RCC-8 AutoResearch 任务包

本题用作者发布的训练 CSV 与 Figure 4 的 24 组 RCC-8 测试 CSV。Agent 只提交 `method.py` 来改进图关系推理；固定 seed 42 的全 24 组等权宏平均是主指标。归一化 `score=(A-B)/(1-B)` 是本题的 AutoResearch 评分约定，不是论文指标。Baseline 为查询感知 R-GCN 适配，Reference 为 EpiGNN-min 适配，均非逐 bit 论文复现。

## 运行拓扑

Harbor 和 Docker 在本机，构建 Agent 与独立 Verifier 的 CPU 容器。GPU 服务器保有代码、数据、CUDA Python、训练过程和 checkpoint。Agent 可通过 SSH 以低权限用户执行任意远端 shell 命令、编辑方法、训练并读取日志；独立 Verifier 使用另一把 SSH key 在远端执行正式评分。具体目录、身份配置和启动前环境变量见 [HARBOR_HANDOFF.md](HARBOR_HANDOFF.md)。Agent 的 `-a`、`-m` 和模型认证由任务方准备。

- `workspace/harbor_task/` 是交给 Harbor 的任务根；Agent 镜像从 `environment/` 构建，只含公开训练资产、R-GCN Starter 和 SSH 客户端。
- `workspace/harbor_task/solution/` 是 Oracle 专用 Reference 和入口；普通 Agent 镜像中的方法从公开 Starter 初始化。Harbor 的唯一提交 artifact 是 `method.py`。
- `workspace/harbor_task/tests/` 构建独立 Verifier 镜像，含可信评分代码与原始 24 组测试 CSV。服务器上对应目录由 root 管理，测试数据仅 root 可读。
- `workspace/reference/` 是出题方 Reference，不在 Agent 构建上下文。
- `optimization_evidence/`、`expert_evidence/` 保存未来实测的成对证据与研究轨迹；不能以空目录代替结果。

## 当前状态

已完成本机 Harbor 0.23.0 schema 解析、109 项静态预检、3 项文件合同检查，以及远端 SSH 身份与权限的非训练检查。未运行模型训练、smoke、Docker build、Harbor Trial 或 Agent 研究。当前 `tests/anchors.json` 不存在，正式 Verifier 会失败，不会产生 reward。静态检查只说明题包结构自洽，不代表端到端验收通过。

公开迭代入口在 Agent 容器中：

```bash
bash /workspace/solution/solve.sh /workspace/output/dev42 42
bash /workspace/solution/solve.sh /workspace/output/smoke42 42 smoke
```

这些命令通过 SSH 在远端执行，日志会回到命令行。本机输出目录只收集结果与逐轮日志，远端保留完整 checkpoint。正式 Verifier 在独立容器运行 `/tests/test.sh`，把最终方法送到远端从头训练与评分，最终写 `/logs/verifier/reward.txt`。

## 尚需在获准实验后完成

用同一冻结协议和 seed 42 实测 Baseline 与 Reference、独立重载并生成可信 `anchors.json`；再验证 CPU 镜像构建、Harbor artifact 交接、完整远端评分、资源/时限、12 小时稳定性和两条真实 Agent 研究轨迹。单 seed 无法估计跨运行波动，也不能满足原教程的 `3σ_B` 随机性门槛，这一协议偏离需由任务方接受。历史其他协议的试跑不能作为本题锚点。
