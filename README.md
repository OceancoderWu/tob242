# ToB 242：论文 RCC-8 benchmark 的 AutoResearch 准备包

本包按 Example 的目录与八章节题面组织，使用论文原始数据和测试题，目标是改进短链训练到长链测试的关系推理泛化。Baseline 是 R-GCN 适配，Reference 是作者 EpiGNN-min 适配。它是准备中的任务设计与评测实现草案；最终验收状态见 `expert_evidence/run_summary.json`，不能仅因目录齐全就称正式任务通过。

## 目录

- `workspace/harbor_task/instruction.md`：给 Agent 的题面。
- `workspace/harbor_task/solution/method.py`：R-GCN 起点；Agent 唯一可修改文件。
- `workspace/harbor_task/tests/`：统一训练、评分、静态边界检查、verifier。
- `workspace/harbor_task/environment/public_assets/`：原始训练 CSV、数据哈希清单和冻结协议；Agent 镜像只复制这部分。
- `evaluation_assets/data/`：原始 24 个测试 CSV，由评分侧单独挂载到 `/opt/benchmark/data`，不复制进 Agent 镜像。
- `workspace/reference/`：出题者保管的 EpiGNN-min，不进入 Agent 镜像。
- `optimization_evidence/`：预留成对三 seed 训练证据的位置；本次没有正式结果或锚点。
- `expert_evidence/PROTOCOL_ALIGNMENT.md` 与 `EVAL_AUDIT.md`：逐项论文对应、作者 Eval 核查、正文/代码冲突和复现局限。
- `expert_evidence/SOURCE_PROVENANCE.md` 与 `BASELINE_LINEAGE.md`：Reference 官方源码和服务器已训练 R-GCN 起点的来源核查。
- `expert_evidence/package_audit/PREPARATION_CHECKLIST.md`：与 Example 的逐项准备对照。
- `expert_evidence/upstream/`：用于核对的上游源码快照，非 Agent 内容。

## 核心协议

原始 train_rcc8.csv 57,600 行；每 seed 80/20 原始行划分；测试全部 k=2–9 × b=1–3，共 153,600 题。40 epochs、batch 128、hidden 32、9 轮、Adam lr=.01、wd=0；验证准确率最高且平局最早。Reference facets=4、margin=1、1 negative；Baseline 保留交叉熵。seeds 为预先固定的 42/43/44，作者具体 seed 列表未公开。

报告全部 24 组的三次均值和 2σ。评分主指标为全部 24 组宏平均；15 组长链均值另报。本包的归一化 score 是 AutoResearch 合同，不是论文指标。论文正文与代码存在 facets/优化器差异，本包优先正文，见对应表。

公开原题不等于独立未公开 Hidden。本包不会为了“隐藏”生成新题。若平台要求未公开测试集，必须先解决与“原始论文题目”之间的要求冲突。

## 未来试跑入口（本次不执行）

推荐 Linux x86_64 / CUDA 11.8 兼容驱动 / 24 GiB GPU。真实预跑环境记录在各运行 `provenance.json`。本地 macOS 只能做静态校验/容器构建，不能替代 GPU 端到端验证。

```bash
# 当前目录为 tob242；不覆盖已有输出。
PYTHON=/path/to/python DATA=$PWD/workspace/harbor_task/environment/public_assets/data TEST_DATA=$PWD/evaluation_assets/data bash expert_evidence/run_pair.sh
# 完成六次训练与六次独立重载后，自动生成 comparison_summary.json 和 anchors.json。
```

单次 smoke 和重载：

```bash
python workspace/harbor_task/tests/train_eval.py \
  --method workspace/harbor_task/solution/method.py --seed 42 \
  --output output/smoke001 --test-data ../../evaluation_assets/data --smoke
python workspace/harbor_task/tests/train_eval.py \
  --method workspace/harbor_task/solution/method.py --seed 42 \
  --output output/reload001 --test-data ../../evaluation_assets/data --reload optimization_evidence/baseline_runs/seed_42/best.pt
```

## 未来容器与部署（本次不执行）

```bash
cd workspace/harbor_task
docker build --platform linux/amd64 -t tob242-rcc8:prep -f environment/Dockerfile .
```

可信评测宿主提供只读 `anchors.json` 和原始测试 CSV，分别挂载到 `/opt/benchmark/anchors.json`、`/opt/benchmark/data`；挂载可写日志与输出目录。必须通过宿主强制 `--network none --gpus device=0 --cpus 8 --memory 16g --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges` 及总时限，并检查持久化输出文件的权限。不要把 `workspace/reference`、出题者源码或正式训练 checkpoint 放入 Agent 镜像。

当前 Dockerfile 为同进程 Python 训练器提供非 root 运行环境。原始测试 CSV 已从 Agent 镜像移出，计划由评分侧挂载。AST 检查不是对恶意 Python 的可靠沙箱，模型与评测器仍同进程；正式对抗性评测还需平台进程/文件隔离、可信指标复测。只读挂载不能防止同进程读取公开答案，行为约束不能替代这一局限的披露。

`tests/test.sh` 只做无 GPU 的准备结构检查；未来正式评分入口为 `tests/verify.sh`，它在完整 grader 通过后写 `/logs/verifier/reward.txt`。缺锚点/超时/错误不会写伪造的零分成功。`task.toml` 是 Example 教学格式，实际 Harbor 原生配置与执行仍需验证。

## 正式发布的剩余门槛

本次仅交付设计与准备文件。此前启动的成对训练已按用户要求停止；其残留文件不得作为正式锚点。未来若决定进入试跑阶段，再按冻结协议完成六次训练及 checkpoint 复测，并核定 Reference 分差、耗时、显存、容器与平台验收。正式 Agent 研究轨迹也尚未开展。记录真实失败，不通过修改题库或倒推评分上限制造通过。
