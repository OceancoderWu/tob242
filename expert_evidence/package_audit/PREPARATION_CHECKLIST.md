# ToB 242 交付检查表

本轮只检查和修复准备工作；没有开展任何模型实验或 Harbor Trial。

| 检查项 | 状态 |
|---|---|
| 目标、唯一可改方法文件、单 seed 42、公开/正式指标 | 已写入题面并经静态核对 |
| 原始训练与 24 组测试 CSV、SHA-256 | 静态核对通过 |
| 本机 Harbor/Docker CPU 镜像配置 | Harbor 0.23.0 schema 解析通过；尚未 build |
| Agent→远端公开训练 SSH 桥 | 脚本与远端目录已部署；key 权限非训练检查通过；尚未运行训练 |
| Agent 可执行任意远端命令但不获 root | 非训练命令与 PTY 检查通过；远端身份为 `researcher` |
| 独立 Verifier→远端正式评分 SSH 桥 | 脚本与 root key 已部署；尚未运行评分 |
| 远端 Python/CUDA 依赖 | `researcher` 下导入 PyTorch/PyG/scatter 通过；尚未训练 |
| 静态预检和合同检查 | 109/109 与 3/3 通过 |
| Baseline/Reference 单 seed 成对证据、可信锚点 | 未生成；正式 reward 当前不可用 |
| Docker build、完整 Harbor Trial、12h 稳定性 | 未运行 |
| 两条 Agent 研究轨迹 | 未运行 |
| 原教程 `3σ_B` 随机性门槛 | 单 seed 无法验证，需任务方接受此协议偏离 |

当前状态是**准备文件和远端权限已接线，正式运行尚待实验阶段验收**。具体拓扑与主机变量见 `tob242/HARBOR_HANDOFF.md`。
