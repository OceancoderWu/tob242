# ToB 242 交付检查表

此表记录实际状态，不以目录存在代替运行证据。

`python3 expert_evidence/preflight.py --report expert_evidence/package_audit/static_preflight.json` 已完成只读检查；结果 `STATIC_READY` 只表示准备文件自洽，不表示任何实验或平台验收通过。

| 检查项 | 当前状态 | 证据或下一步 |
|---|---|---|
| 三目录职责、八章节题面、Starter/Reference 分离 | 已实现，静态检查 | `workspace/harbor_task/`、`workspace/reference/`、`instruction.md` |
| 原始训练与 24 组测试数据 | 文件和哈希已核对 | `manifest.json`、`tests/benchmark_data/`；测试集公开，不称为新 Hidden |
| Public/Dev 可用入口 | 已实现，未做 GPU 动态验证 | `solution/solve.sh` → `--public-dev`，不读取测试 CSV |
| Harbor 原生配置 | 当前独立 Verifier 版通过本机 0.23.0 schema 静态加载；未运行本版 dry-run | `task.toml`；目标平台版本若不同需重新验证 |
| Docker 原生构建路径 | Agent 与独立 Verifier 两套 context 已接线，未实际 build | `environment/Dockerfile`、`tests/Dockerfile`、两套公开资产镜像 |
| Verifier 入口与 reward | 代码已接通，未做 GPU Trial | `/tests/test.sh` → `grader.py` → 原子 reward.txt |
| 测试标签与候选隔离 | 独立 Verifier、root/普通用户进程分离已实现，未在目标容器验证 | `task.toml` artifact、`tests/Dockerfile`、`grader.py`、`inference_worker.py` |
| Baseline/Reference 真实成对训练 | 未运行 | 固定 seed 42 各自训练、重载和规范证据 |
| Reference [0.15,0.8] 与正向改善 | 未验证 | `comparison_summary.json` 完整原始结果复算后判断 |
| 教程的随机性质量门 | 无法按单 seed 验证 | `3σ_B` 需要多次 Baseline 训练；任务方须接受该偏离 |
| 正式评分锚点 | 未生成 | 通过质量门后由 `summarize.py` 部署 `tests/anchors.json` |
| 两条 Agent 有效研究轨迹 | 未运行 | 两种模型组合各至少 10h，有效时长和结果凭真实日志填写 |
| 12h 容器稳定性、资源和 Harbor 正式 Trial | 未运行 | 目标 GPU/Linux 平台构建与长时验证 |

`tests/hidden_assets/` 在交付时为空；若平台另要求真正未公开测试题，须先决定是否允许偏离论文原始测试集。正式发布仍需真实运行证据，并由任务方处理单 seed 与教程随机性质量门不一致的问题。
