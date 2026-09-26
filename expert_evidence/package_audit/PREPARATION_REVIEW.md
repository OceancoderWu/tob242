# ToB 242 准备工作复核

本轮按用户指定拓扑修复：Harbor/Docker 在本机，两个镜像都只需 CPU；代码、数据、CUDA 环境、训练与正式评分在远端 GPU 服务器。**未启动模型训练、smoke、Docker build、Harbor Trial 或 Agent 研究。**

## 已完成

| 范围 | 当前实现 |
|---|---|
| Agent/Oracle 边界 | Agent 镜像从公开 R-GCN Starter 初始化；Oracle 方法仍在 Harbor `solution/`，并与出题方 Reference 相同。只声明最终 `method.py` artifact。 |
| Harbor 资源与网络 | `task.toml` 声明本机 `gpus=0`、出站网络、独立 Verifier；Agent key 与 Verifier key 分别由主机变量注入。Harbor 0.23.0 schema 静态加载通过。 |
| 本机镜像 | 两个 Dockerfile 都改为 CPU SSH 客户端镜像，不安装 CUDA、PyTorch 或 PyG。Agent 构建上下文不含测试 CSV 或 Reference。 |
| 远端公开入口 | `remote_runtime/public/run.sh` 接收候选方法，作为 `researcher` 使用远端固定 CUDA Python 运行 public-dev/smoke；CLI 返回日志并复制三个公开结果文件。公开训练器 root 拥有、只读。 |
| 远端正式入口 | `remote_runtime/private/verify.sh` 接收最终方法与可信锚点，以 root 启动固定 grader；候选训练/推理切换 `researcher`，测试 CSV 目录为 0700。评分标量返还本机独立 Verifier。 |
| SSH 隔离 | Agent key 可执行任意远端 shell 命令，但强制入口先降权为 `researcher`。旧 Reference 所在目录及其他非公开工作目录为 0700，`researcher` 读取正式测试被拒绝。Verifier 专用 root key 不在 Agent 镜像或其环境变量中。SSH host key 已固定。 |
| 静态一致性 | 数据 SHA-256、镜像源文件、题面/脚本副本、Python/Bash 语法及合同检查均已完成；结果见 `static_preflight.json`。 |

## 尚待获准实验后验证

1. 当前单 seed 42 的 Baseline/Reference 成对训练、独立重载和 24 组测试证据；可信锚点 `tests/anchors.json` 尚未生成。因此正式入口目前会明确失败。
2. 本机两套 CPU Docker 镜像构建、Agent/Verifier 容器内 SSH、Harbor artifact 转交、正式 reward、资源与时限、12 小时稳定性。
3. 两条真实 Agent AutoResearch 轨迹。单 seed 不能验证教程的 `3σ_B` 随机性门槛，需要任务方接受偏离。

原始论文测试题本来公开；运行时权限隔离不能把它们变成新建未公开 Hidden。当前结论为**静态接线完成，端到端验收未完成**。
