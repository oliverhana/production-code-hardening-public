# production-code-hardening

> ⚠️ **Notice / 声明**
>
> This repository is a **sanitized** portfolio version — all secrets, real personal data, and confidential business logic have been removed or replaced with program-generated synthetic data. **Some proprietary/commercial code is not open-sourced.** Provided **for learning and exchange only — commercial use is NOT permitted.** Pending the author's review before any public release.
>
> 本仓库为**已脱敏**的作品集版本 —— 所有密钥、真实个人数据与商业机密逻辑均已移除或用程序生成的假数据替换。**部分商业代码未公开。仅供学习与交流,不可用于商用。** 待作者审核后再行公开。


**English** | [中文](#中文)

> A reusable Codex/agent skill that turns a prototype or internal service into a defensible production candidate — treating implementation, tests, migration safety, runtime config, and release evidence as one deliverable.

## Overview

The core shift it encodes: move from *"find bugs"* to **define system invariants → enforce them in code → prove them with fault injection → separate code-complete from operator-owned go-live blockers**. It ships a deterministic quality-gate runner that produces machine-readable release evidence.

## What it does

- **Sets the operating mode** from the request (review vs. harden) before touching anything; never lets "make it production-ready" authorize deployment, credential rotation, external messaging, or history rewriting.
- **Models the system before patching** — process boundaries, state machines, external side effects, trust boundaries, concurrency domains, resource ownership, and sensitive-data flows.
- **Converts risks into enforceable invariants** — program constraints over prompt wording: strict schema validation at every output boundary, mandatory business ops executed in code (not `tool_choice="auto"`), untrusted input treated as data, pinned model/provider config.
- **Proves the result** with tests, fault injection, and a release evidence ledger, and distinguishes code-complete findings from operator blockers (DNS, TLS, SSO, KMS, real credentials, third-party consoles).

## Tech stack

- Codex/agent skill (Markdown `SKILL.md` + reference checklists).
- `scripts/run_quality_gates.py` — Python 3 standard library only (argparse, subprocess, json); no third-party dependencies.
- Uses the project's own toolchain at runtime: `git`, `python -m compileall`, `unittest`/`pytest`, `coverage`, `pip check`.
- `agents/openai.yaml` — agent interface metadata.

## Usage

```bash
git clone https://github.com/<owner>/production-code-hardening.git ~/.codex/skills/production-code-hardening
```

Invoke the skill for enterprise-readiness reviews, production refactors, or investigations into state machines, async races, deadlocks, resource leaks, exception paths, DB migrations, webhooks & idempotency, PII protection, LLM schema/tool boundaries, external-service retries, test gaps, coverage, or go-live gates.

## Usage example

Run the deterministic, shell-free quality gates and emit JSON evidence:

```bash
python3 scripts/run_quality_gates.py \
  --project /path/to/project \
  --python /path/to/project/.venv/bin/python \
  --coverage \
  --coverage-fail-under 85 \
  --report /tmp/quality-gates.json
```

The runner checks `git diff --check`, compiles Python, auto-detects `unittest` vs. configured `pytest`, runs tests with optional coverage, verifies dependencies with `pip check`, uses bounded timeouts, and returns nonzero if a required gate fails. Pass `--max-output-chars=0` to omit captured command output from the report.

## Structure

```
SKILL.md                              # baseline → model → invariants → verify → gate
references/audit-checklist.md         # enterprise-grade review checklist
references/state-machine-review.md    # state machine & side-effect analysis
scripts/run_quality_gates.py          # automated release quality gates
agents/openai.yaml                    # agent interface config
```

---

<a name="中文"></a>

# production-code-hardening

[English](#production-code-hardening) | **中文**

> 一个可复用的 Codex/agent skill:把原型或内部服务打造成经得起检验的生产候选——把实现、测试、迁移安全、运行时配置与发布证据当作**一个整体交付物**。

## 项目简介

它沉淀的核心转变:从「发现 Bug」升级为 **定义系统不变量 → 代码强制执行 → 故障注入验证 → 区分「代码完成」与「外部上线阻断」**。附带一个确定性质量门禁运行器,产出机器可读的发布证据。

## 能做什么

- **先定操作模式**(审查 vs 加固)再动手;绝不让「生产化」授权部署、轮换凭证、对外发消息或改写历史。
- **打补丁前先建模** — 进程边界、状态机、外部副作用、信任边界、并发域、资源归属、敏感数据流。
- **把风险转成可强制的不变量** — 用程序约束而非提示词:每个输出边界严格 schema 校验、必做业务操作用代码执行(而非 `tool_choice="auto"`)、不可信输入当数据不当指令、显式固定模型/供应商配置。
- **用证据证明结果** — 测试、故障注入、发布证据台账;并区分「代码层已完成」与「运维方负责的上线阻断项」(DNS、TLS、SSO、KMS、真实凭证、第三方后台)。

## 技术栈

- Codex/agent skill(Markdown `SKILL.md` + 参考清单)。
- `scripts/run_quality_gates.py` — 仅用 Python 3 标准库(argparse、subprocess、json),无第三方依赖。
- 运行时调用项目自身工具链:`git`、`python -m compileall`、`unittest`/`pytest`、`coverage`、`pip check`。
- `agents/openai.yaml` — agent 接口元数据。

## 如何使用

```bash
git clone https://github.com/<owner>/production-code-hardening.git ~/.codex/skills/production-code-hardening
```

用于企业级上线评审、生产化重构,或涉及状态机、异步竞态、死锁、资源泄漏、异常路径、数据库迁移、Webhook 与幂等、PII 保护、LLM schema/工具边界、外部服务重试、测试缺口、覆盖率、上线门禁的排查。

## 用法示例

运行确定性、不经过 shell 的质量门禁,产出 JSON 证据:

```bash
python3 scripts/run_quality_gates.py \
  --project /path/to/project \
  --python /path/to/project/.venv/bin/python \
  --coverage \
  --coverage-fail-under 85 \
  --report /tmp/quality-gates.json
```

运行器会执行 `git diff --check`、编译 Python、自动识别 `unittest` 或已配置的 `pytest`、按需收集覆盖率、用 `pip check` 校验依赖、使用有界超时,任一必需门禁失败即返回非零。加 `--max-output-chars=0` 可在报告中省略捕获的命令输出。

## 目录结构

```
SKILL.md                              # 建基线 → 建模 → 立不变量 → 验证 → 发布门禁
references/audit-checklist.md         # 企业级审查清单
references/state-machine-review.md    # 状态机与副作用分析
scripts/run_quality_gates.py          # 自动化发布质量门禁
agents/openai.yaml                    # agent 接口配置
```
