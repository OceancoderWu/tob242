# ToB 242：本机 Harbor + 远端 GPU 接线

Harbor 0.23.0 和 Docker 运行在本机。Agent 与独立 Verifier 都是本机 CPU 容器；它们通过固定端口的 SSH 连接 GPU 服务器。PyTorch、数据、训练器、checkpoint 和正式评分都在服务器。Agent 的模型类型、`-a`/`-m` 及模型服务认证由任务方提供。

## 已部署的远端目录

| 目录 | 权限与用途 |
|---|---|
| `/root/autodl-tmp/autore/harbor242-public` | 公开训练 CSV 和只读训练器；Agent 可通过 SSH 以 `researcher` 身份执行普通 shell 命令，编辑 `solution/method.py` 并运行训练。`solution/`、`output/` 可写。 |
| `/root/autodl-tmp/autore/harbor242-private` | root 管理的正式 grader、24 组测试 CSV 和未来锚点；`benchmark_data` 为 0700。Verifier key 只注入独立 Verifier 阶段。候选训练和推理仍作为 `researcher` 运行。 |
| `/root/autodl-tmp/autore/envs/research` | 远端现有 CUDA Python 环境；已做非训练的依赖导入检查。 |

远端 `/root` 设置为 0711，以便低权限训练进程执行现有 Python；目录不可列举。旧 `paper242`、实验日志、原始数据和其他非公开工作目录已收紧为 0700。Agent SSH key 在 root `authorized_keys` 中绑定强制降权入口：任意 SSH 命令或交互 shell 都以 `researcher` 运行，不获得 root。私有 key 位于本机 `~/.ssh/tob242_agent` 和 `~/.ssh/tob242_verifier`，不在题包或 Docker 构建上下文。服务器 host key 固定在 `environment/known_hosts` 并镜像到 Verifier。

## Harbor 入口

`task.toml` 不向本机 Docker 申请 GPU，启用容器出站网络以访问 SSH 服务器和 Agent 模型服务。`environment/Dockerfile` 与 `tests/Dockerfile` 是本机 CPU 镜像。Agent 改 `/workspace/solution/method.py`，然后执行：

```bash
bash /workspace/solution/solve.sh /workspace/output/dev42 42
bash /workspace/solution/solve.sh /workspace/output/smoke42 42 smoke
```

脚本把本机当前方法通过 SSH stdin 送到远端训练入口，命令行实时接收训练日志，并把 `result.json`、`provenance.json`、`epochs.jsonl` 复制回本机指定输出目录。公开训练与正式评分共用远端 GPU 文件锁，避免两种任务同时占卡。每轮必须使用新的目录名。

Agent 也可用 `bash /workspace/tests/remote_client.sh agent '任意远端命令'` 直接操纵服务器，或省略命令进入交互 shell。远端默认目录是 `harbor242-public`，身份是 `researcher`。如果直接编辑远端 `solution/method.py`，提交前执行 `bash /workspace/tests/sync_method_from_remote.sh`，把它同步回 Harbor 唯一方法 artifact。本机 `solution/solve.sh` 会把本机方法送到远端，因此两种编辑流程不要混用而忘记同步。旧 Reference 与正式测试文件由 Linux 文件权限隔离。

Harbor 只向独立 Verifier 转交最终 `method.py`。`/tests/test.sh` 将方法与可信锚点经 Verifier 专用 SSH key 送到远端，远端 root grader 从头训练、读取 24 组测试并计算 reward。返回的有限标量写在本机 `/logs/verifier/reward.txt`。单 seed 固定为 42。

## 任务方启动前设置

在启动 Harbor 的同一终端，注入 SSH key 的 base64 值；不要把值写入 `task.toml` 或提交到 Git：

```bash
export T242_AGENT_KEY_B64="$(base64 < ~/.ssh/tob242_agent | tr -d '\n')"
export T242_VERIFIER_KEY_B64="$(base64 < ~/.ssh/tob242_verifier | tr -d '\n')"
```

Harbor 配置只引用这两个主机环境变量。任务方另行设置真实 Agent、模型和认证。远端准备脚本为 `remote_runtime/prepare_server.sh`，已执行一次；若重建服务器，需先重新部署文件和两个授权公钥。不要在容器里放入远端 root 密码。

## 当前验收边界

已完成：Harbor schema 静态解析、文件合同与语法检查、远端文件部署、SSH 身份隔离和 CUDA 依赖的非训练导入检查。**未执行**模型训练、smoke、Docker build、Harbor Trial 或 Agent 研究。`tests/anchors.json` 仍需在获准实验后由同一 seed 42 的 Baseline/Reference 实测生成；因此当前正式 Verifier 会明确失败，不会给出伪分数。镜像构建、端到端命令、长时稳定性和真实 Harbor artifact 交接也尚未动态验收。

## 实验启动顺序

当前协议已单独部署在服务器的 `/root/autodl-tmp/autore/paper242/tob242-seed42-ready`；它与本机关键脚本、Reference、训练器和协议的哈希一致，25 个训练/测试 CSV 的哈希也已复核。旧的 `paper242/tob242` 是另一版协议，不要在旧目录生成本题锚点。

先在服务器执行固定 seed 42 的 Baseline/Reference 训练和独立重载。长时任务建议用 `nohup` 启动，命令如下；**执行这段才会真正开始实验**：

```bash
ssh -T -i ~/.ssh/tob242_verifier -p 14755 root@connect.bjb1.seetacloud.com <<'REMOTE'
set -e
cd /root/autodl-tmp/autore/paper242/tob242-seed42-ready
test ! -e optimization_evidence/run_pair.console.log
nohup env PYTHON=/root/autodl-tmp/autore/envs/research/bin/python \
  bash expert_evidence/run_pair.sh \
  > optimization_evidence/run_pair.console.log 2>&1 < /dev/null &
echo "remote PID=$!"
REMOTE
```

用同一 SSH key 查看 `optimization_evidence/run_pair.console.log` 及 `baseline_runs/seed_42.run.log`、`reference_runs/seed_42.run.log`。结束后必须确认远端 `optimization_evidence/comparison_summary.json` 的 `status` 是 `COMPLETE`，且生成了 `workspace/harbor_task/tests/anchors.json`。失败时保留日志与结果，不修改 seed 或手工制造锚点。

将远端 `optimization_evidence/` 全部同步回本机同名目录，然后在本机运行 `python3 expert_evidence/summarize.py`（从 `tob242/` 执行），由本机证据再生成正式锚点。随后导出上文两个 SSH 环境变量，在本机依次运行 Harbor dry-run、Oracle Trial，验证本机 CPU 镜像、独立 Verifier、远端评分和 reward。Oracle 通过后，用任务方准备的真实 `-a`、`-m` 与认证启动 Agent AutoResearch。Harbor 本机 CLI 支持 `-p`、`-a`、`-m`、`-e docker`、`-n 1`、`--dry-run` 和 `--force-build`。
