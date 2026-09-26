# 关系图上的跨长度泛化

## 1. 目标

给定带 RCC-8 关系的有向图和有序查询节点对，训练模型预测查询关系。你只提交 `solution/method.py`；目标是在固定 seed 42 下提高原始 RCC-8 测试题全部 24 个 `(k,b)` 组的宏平均准确率。初始方法是可运行的查询感知 R-GCN。

## 2. 任务背景与数据

八个类别依次为 `DC, EC, EQ, NTPP, NTPPI, PO, TPP, TPPI`。输入边关系是已知事实，查询对的关系是答案，节点编号只在一张图内标识节点。

公开训练文件 `environment/public_assets/data/train_rcc8.csv` 有 57,600 行，链长 `k=2–4`、路径数 `b=1–3`。每个 seed 使用 PyTorch `random_split` 按原始行划分 80% 训练、20% 验证，不去重。Public/Dev 命令只使用这份训练文件的训练和验证部分；smoke 只用于接口检查，不能当作正式分数。

正式测试沿用已公开的论文原始测试 CSV：`k=2–9`、`b=1–3`，共 24 文件、153,600 题。它们只存于独立 Verifier 镜像的 `/tests/benchmark_data`，不在 Agent 镜像或工作区。这些题目本身已经公开，不能视为新建的未公开 Hidden；提交方法不得在运行时读取测试文件、标签或评分结果。训练分布外的 `k=5–9` 共 15 组另作诊断指标。

## 3. 指标与评分

正式评测固定 seed `42`，从头训练一次，在验证准确率严格提高时保存 checkpoint；平局保留最早轮次。固定 checkpoint 后，Verifier 对 24 组逐组计算 accuracy，再求 24 组等权宏平均作为主指标 `A`。另报告每组 accuracy 和长链 15 组的等权宏平均；单 seed 不计算跨运行标准差或误差区间。

归一化分数为 `score=(A-B)/(1-B)`，其中 `B` 是出题方用同一 seed 42 和相同协议实测的 Baseline 主指标。分数连续、不裁剪；Baseline 对应 0，准确率上限 1 对应 1。该标量是 AutoResearch 任务约定；论文 Figure 4 的逐组 accuracy 才是与论文对照的指标。本题只做单 seed 比较，正向改善定义为 `A>B`；它不能估计训练随机波动，也不以 `3σ_B` 判定提升。正式锚点由 Verifier 使用，Agent 不能改写。

Public/Dev 反馈是单 seed 的验证准确率，**不是**上式的正式 benchmark 分数。可以据此选方法；不得按正式测试表现选择中间 checkpoint。

## 4. 可修改范围与接口

只修改 `/workspace/solution/method.py`。可研究模型结构、关系表示、消息传播、聚合、查询读出及训练损失；不要求复现任何特定参考方法。文件必须定义：

```python
def build_model(num_relations=8, num_steps=9):
    # 返回 torch.nn.Module
    ...

def training_loss(logits, targets):
    # 返回有限的标量 Tensor
    ...
```

`model(graph)` 返回 `[B,8]` 的有限 logits。`graph` 只含 `edge_index[2,E]`、`edge_type[E]`、`query_index[2,B]`、`batch[N]`、`num_nodes`；标签只传给 `training_loss`。图张量在远端训练进程中放到 GPU；本机 Harbor 容器不申请 GPU。`num_steps=9` 和 Starter 的表示宽度 32 是起始设置，不限制合法结构探索；模型参数总数必须不超过 2,000,000。只能使用远端预装的 PyTorch、PyG、torch-scatter、NetworkX、typing 和 math，不能下载模型或添加外部权重。

## 5. 硬边界与统一实验参数

正式评测使用 seed `42`、40 epochs、batch size 128、Adam、learning rate 0.01、weight decay 0；不使用 scheduler 或梯度裁剪。数据划分和样本顺序由共同训练器确定，Baseline 与候选遵守同一规则，均从头初始化。总参数量上限 2,000,000；训练进程上限 7,200 秒，正式 Verifier 总上限见 `task.toml`。

不能修改训练器、评分器、测试资产、协议和锚点，不能通过提交方法读取文件、环境变量、网络、外部进程或测试答案；不能硬编码测试题或逐题结果。Harbor 将最终 `method.py` 作为唯一候选 artifact 送入独立 Verifier 容器。Verifier 会拒绝非白名单导入及常见文件、进程 API；远端正式测试文件仅 root 可读，候选在远端低权限子进程中训练和推理。检测到越界或输出格式错误时评分失败。容器网络用于 SSH 和 Agent 模型服务；模型代码本身不能访问网络。

## 6. 提交要求

最终 `solution/` 只能有 `method.py` 与固定的 `solve.sh`；仅 `method.py` 可改。不要提交 checkpoint、日志或自报成绩。正式 Verifier 重新从头训练并自行计算分数，不读取自报结果。

公开完整单 seed 验证命令（输出目录必须尚不存在）：

```bash
bash solution/solve.sh output/dev42 42
```

公开接口 smoke：

```bash
bash solution/solve.sh output/smoke42 42 smoke
```

这两个命令由本机容器通过 SSH 将本机当前 `method.py` 发给远端 GPU 服务器；训练日志直接返回命令行，`result.json`、`provenance.json` 和 `epochs.jsonl` 会复制到本机指定输出目录。远端完整输出（含 checkpoint）留在 `/root/autodl-tmp/autore/harbor242-public/output/<目录名>`。容器内的 `tests/train_eval.py` 只供阅读协议，不能在本机直接运行训练。上述两个入口只使用公开训练 CSV，不需要正式测试资产或评分锚点。运行前，任务方需向 Harbor 注入 `T242_AGENT_KEY_B64`；不要把 SSH 私钥写进 `method.py` 或题包。

你也可以直接通过 SSH 在 GPU 服务器上运行任意普通用户命令，例如查看 GPU、编辑公开工作区中的方法、检查日志或运行公开训练器：

```bash
bash tests/remote_client.sh agent 'pwd; nvidia-smi'
bash tests/remote_client.sh agent 'cat /root/autodl-tmp/autore/harbor242-public/solution/method.py | /root/autodl-tmp/autore/harbor242-public/run.sh public-dev dev42 42'
bash tests/sync_method_from_remote.sh
```

SSH 命令以远端 `researcher` 身份执行。若你直接修改了远端 `solution/method.py`，最后必须运行 `sync_method_from_remote.sh`，让 Harbor 提交的本机 `/workspace/solution/method.py` 与远端方法一致。`solution/solve.sh` 会用本机方法覆盖远端方法，适合在本机编辑方法的流程。

## 7. 迭代流程

先跑 smoke 确认接口，再在公开验证集上完成一次训练。每轮改动后比较验证准确率、逐轮训练日志、显存和耗时；保留当前最佳 `method.py`，效果退化时回退，再探索下一种方法。公开验证集可用于研究迭代；正式 24 组测试只由 Verifier 对最终提交评分，不向 Agent 提供逐题标签。

Agent 可使用容器内的 shell 和 SSH 客户端，在远端 `researcher` 账号下执行普通命令、运行已部署的 Python、PyTorch 和其他固定依赖。远端公开工作区的 `solution/`、`output/` 与账号主目录可写，固定训练器、正式测试及出题方 Reference 不可改；不能安装额外依赖。单轮耗时取决于方法；本任务提供 12 小时 Agent 总时限。每轮指定不同的输出目录，不得覆盖其他轮次目录。

## 8. 完成条件

`method.py` 能由共同训练器按 seed 42 从头训练一次，输出合法有限 logits，通过参数量、文件范围、静态边界和低权限推理检查；正式 Verifier 在全部 24 组上产生有限主指标与连续分数。研究目标是得到较 Baseline 正向改善的方法，并完整保留公开迭代的最佳版本。出题方 Reference 的复现、锚点、两条研究轨迹和平台验收由出题方处理，不是 Agent 的提交内容。
