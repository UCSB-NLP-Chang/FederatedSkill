# FederatedSkill: Federated Learning for Agentic Skill Evolution

This is the official implementation of the paper *FederatedSkill: Federated Learning for Agentic Skill Evolution* ([arXiv:2606.03143](https://arxiv.org/abs/2606.03143)).

## Abstract

Modern LLM agents accumulate skills (executable SKILL.md procedures + supporting scripts) as they solve tasks. When several agents work on the same family of tasks but use different backbone models or CLI scaffolds, naively sharing skills hurts more than it helps — a SKILL.md that works on Claude Code may be unparseable to qwen-code, and an OCR umbrella refined by GLM-5 may not transfer to Kimi K2.5. FederatedSkill is a federated learning setup where each client keeps its own private skill library, and a per-client cloud-side merger combines peer trial trajectories into personalized library updates. We release (1) a 20-family task benchmark with verifier scripts; (2) a federation runner with four reproducible settings (SE baseline, homogeneous federation, heterogeneous-model federation, heterogeneous-model-and-CLI federation); and (3) the cloud-merge agent procedure that decides per round whether to absorb, repair, refactor, or drop a peer's skill from the target client's point of view.

## Requirements

### Environment

One command does everything (clones SkillFlow upstream, sets up the venv, downloads the benchmark, pre-pulls the container image):

```shell
bash setup.sh
```

After it finishes, activate the venv and you're done:

```shell
source .venv/bin/activate
```

What `setup.sh` actually does, in order:

1. Installs `uv` (Astral's Python package manager) if missing.
2. Clones [SkillFlow upstream](https://github.com/ZhangZi-a/SkillFlow.git) into `external/SkillFlow/`. The upstream repo ships the benchmark scaffold we depend on (`libs/skill_evolution/`, `libs/harbor_noinstall_agents/`, `libs/terminus_env/`, `libs/terminus_agent/`, and `iterative_shared_skills_runner.py`).
3. Runs `uv sync` inside SkillFlow to create `external/SkillFlow/.venv` with harbor + every dep SkillFlow declares.
4. Writes a `.pth` file into that venv pointing at the SkillFlow source root, so `libs.skill_evolution.patcher`, `libs.harbor_noinstall_agents.agents`, etc. are importable from anywhere — not just from inside the SkillFlow directory.
5. Installs **federate_skill** (this repo's `skillfl/skillflow_adapter/`) as an editable package into the same venv. Our `pyproject.toml` pins harbor to the exact commit the experiments ran against, which uv reconciles against the version SkillFlow pulled.
6. Symlinks `.venv → external/SkillFlow/.venv` at this repo's root so `source .venv/bin/activate` works the way it does in any other Python project.
7. Copies `.env.example → .env` if missing.
8. Downloads `test_tasks/` from HuggingFace ([zhang-ziao/SkillFlow-Task](https://huggingface.co/datasets/zhang-ziao/SkillFlow-Task), ~1.6 GB).
9. Pre-pulls the prebuilt container image used by the per-trial agents and the cloud-skill merger.

Each of those steps can be skipped via env var (see `setup.sh --help`-equivalent comments at the top of the script): `SKIP_IMAGE_PULL=1`, `SKIP_TASKS_DOWNLOAD=1`, etc. Re-running `setup.sh` is idempotent — it pulls SkillFlow upstream, refreshes the venv, and leaves your `.env` alone.

If you'd rather install by hand: replicate `setup.sh` step-by-step. The package layout is:

* `skillfl/skillflow_adapter/` — the federation runner from this paper.
* `external/SkillFlow/` — SkillFlow upstream (created by `setup.sh`; not committed).
* `test_tasks/` — the benchmark dataset (downloaded by `setup.sh`; not committed).
* `harbor` — installed via `uv sync` (git pin in our `pyproject.toml`). Provides the trial orchestrator (`Job`, `JobConfig`, `TrialHookEvent`) that drives each per-task container.

Optional analysis extras (matplotlib) for the plotting helpers:

```shell
uv pip install -e ".[analysis]"
```

### API credentials

```
cp .env.example .env
```

Fill in only the providers you plan to use. Supported providers and their env vars:

| Provider                              | Env vars                  |
| ------------------------------------- | ------------------------- |
| Dashscope (qwen3.6-plus / glm-5)      | `DASHSCOPE_KEY`         |
| Moonshot (kimi-k2.5)                  | `MOONSHOT_KEY`          |
| Anthropic (claude-code merger)        | `ANTHROPIC_API_KEY`     |

`.env` is sourced by the launcher; the configs reference its variables as `$DASHSCOPE_KEY`, `$MOONSHOT_KEY`, etc.

### Container images

The `cloud_skill_merge` merger and every worker trial run inside a podman/docker container. Two layers are involved:

1. **Base image** (`skillflow/harbor-cli-base:ubuntu24.04`, also aliased as `skillevlove/harbor-cli-openhands:ubuntu24.04` for compatibility with the HuggingFace dataset's unmodified Dockerfiles). Contains Ubuntu 24.04 + Node.js + claude-code / qwen-code / kimi-cli / codex / gemini CLIs. Built once via SkillFlow's `docker/harbor-cli-base/build.sh`.
2. **Per-task image** (`harbor-prebuilt:task-<hash>`). Each `test_tasks/<family>/<task>/environment/Dockerfile` builds on top of the base image to add task-specific dependencies and copy task input files.

The base image is **not on a public registry** — `setup.sh` builds it locally from `external/SkillFlow/docker/harbor-cli-base/` on first run (15–30 min, network-heavy). Per-task images build on top in seconds; harbor uses `force_build: True` (see `skillfl/skillflow_adapter/harbor_bridge.py`) so the first trial against each task builds its image and subsequent trials reuse the cache.

To rebuild the base image manually:

```shell
cd external/SkillFlow/docker/harbor-cli-base
bash build.sh skillflow/harbor-cli-base:ubuntu24.04
podman tag skillflow/harbor-cli-base:ubuntu24.04 skillevlove/harbor-cli-openhands:ubuntu24.04
```

On systems where rootless podman cannot delegate the cpu controller, container start can fail with `conmon failed: exit status 1` (the OCI runtime tries to write `cpu.max` in a cgroup that doesn't have the `cpu` controller). Two ways to work around it:

1. (Preferred) Ask the host admin to add `Delegate=cpu cpuset io memory pids` to `/etc/systemd/system/user@.service.d/delegate.conf` and restart `user@$(id -u).service`.
2. (No-root workaround) Edit the harbor `docker-compose-base.yaml` shipped with the SDK to drop the `deploy.resources.limits` block:
   ```yaml
   # Before
   services:
     main:
       volumes: [...]
       deploy:
         resources:
           limits:
             cpus: ${CPUS}
             memory: ${MEMORY}
   # After: drop the entire deploy: block
   ```
   This disables in-container CPU/memory limits but lets the trial start. `pip show harbor` tells you the install path; the YAML is under `<install>/harbor/environments/docker/`.

### Tasks

`setup.sh` downloads `test_tasks/` from HuggingFace ([zhang-ziao/SkillFlow-Task](https://huggingface.co/datasets/zhang-ziao/SkillFlow-Task)) — all 20 families used in the paper (~1.6 GB on disk). To re-fetch by hand:

```shell
.venv/bin/hf download zhang-ziao/SkillFlow-Task --repo-type dataset --local-dir test_tasks
```

Each family directory has 8–9 sub-task directories with `task.toml`, `instruction.md`, `environment/` (the bundle harbor mounts into the container), `solution/` (reference), and `tests/` (verifier).

```jsonc
test_tasks/
├── Production-Capacity-Planning/
│   ├── ALL_TASK_DIFFICULTY_RANKING.json   // round order
│   ├── harbor_gdpval_36_task1/
│   │   ├── task.toml                       // metadata + timeouts
│   │   ├── instruction.md                  // agent prompt
│   │   ├── environment/
│   │   │   ├── Dockerfile
│   │   │   └── copy_of_capacity_sheet.xlsx
│   │   ├── solution/                       // reference outputs
│   │   └── tests/                          // verifier scripts
│   └── ...
├── OCR-Data-Extraction/
├── Healthcare-Cost-Benefit-Analysis/
└── ... 17 more families
```

## Usage

### Run a setting

Each setting has a one-line wrapper under `scripts/` that reads `.env`, activates the venv, and dispatches to the right entry point (`python -m skillfl.skillflow_adapter.cli` for settings 2–4, `external/SkillFlow/iterative_shared_skills_runner.py` for setting 1). The four configs in `configs/` reproduce the paper's four headline settings:

| #  | Config                                  | Setting                                                                              |
| -- | --------------------------------------- | ------------------------------------------------------------------------------------ |
| 1  | `1_se_qwen.local.yaml`                | Self-Evolve baseline. Single qwen3.6-plus worker, no federation.                     |
| 2  | `2_fed_3glm_cc.local.yaml`            | Federation, homogeneous: three GLM-5 workers, all on claude-code.                    |
| 3  | `3_fed_hetero_cc.local.yaml`          | Federation, heterogeneous backbone: qwen / glm / kimi on a shared claude-code CLI.   |
| 4  | `4_fed_hetero_mixed_cli.local.yaml`   | Federation, heterogeneous backbone + CLI: qwen-code / claude-code / kimi-cli triple. |

The main arguments:

```text
--config                  Path to YAML config.
--only-family             Restrict the run to a single family by name.
--max-parallel-groups N   Run N families in parallel (subprocess per family).
                          Default 10; use 1 for in-process / smoke runs.
```

Example — setting 3 (heterogeneous CC-CLI), one family for a quick smoke test, via the shell wrapper:

```shell
FAMILY=Production-Capacity-Planning bash scripts/run_3_fed_hetero_cc.sh
```

Example — same thing via the Python entry point directly (after activating the venv):

```shell
source .venv/bin/activate
python -m skillfl.skillflow_adapter.cli \
    --config configs/3_fed_hetero_cc.local.yaml \
    --only-family Production-Capacity-Planning \
    --max-parallel-groups 1
```

Example — setting 1 (SE baseline) on the same family:

```shell
FAMILY=Production-Capacity-Planning bash scripts/run_1_se.sh
# or, equivalently:
source .venv/bin/activate
python external/SkillFlow/iterative_shared_skills_runner.py \
    --config configs/1_se_qwen.local.yaml \
    --max-parallel-groups 1
```

Outputs land under the path configured by `runs_root` in the YAML (default: `jobs/<job_name>/<family>/`). Each family directory has:

```
runs_root/<job_name>/<family>/
├── shard_manifest.json               // partition of tasks → worker shards
├── family_summary.json               // final rewards + elapsed
├── shared_skills/                    // (shared-merger mode) merged library
├── worker_skills/u{i}/               // (unshared mode) per-worker library
├── cloud_skill_merge_sandboxes/u{i}/ // per-round merger workspaces
│   └── library/                      // target worker's library post-merge
└── round_<NNN>/
    ├── round_summary.json
    ├── worker_<i>/
    │   ├── <trial_name>/             // harbor's per-trial output
    │   │   ├── agent/                // agent CLI logs + sessions
    │   │   ├── verifier/             // sub-test results (ctrf.json)
    │   │   └── result.json
    │   └── patch.json                // per-worker distilled patch
    └── merged_for_u{i}/merged_patch.json
```

### Inspect a run

`family_summary.json` carries the headline numbers:

```json
{
  "family_name": "Production-Capacity-Planning",
  "n_workers": 3,
  "n_rounds": 9,
  "elapsed_sec": 27184.4,
  "reward_stats": {
    "n": 27,
    "mean": 0.667,
    "max": 1.0,
    "min": 0.0,
    "n_passed": 18
  },
  "merger_cost_total_usd": 1.42
}
```

For per-round trace, `round_<NNN>/round_summary.json` shows each worker's `(task, reward, exception?)` plus the merger's per-target cost.

## Reproduce results in the paper

Each of the four configs sweeps one family per launch. To loop over all 20 families:

```shell
for fam in $(ls test_tasks/); do
  python -m skillfl.skillflow_adapter.cli \
      --config configs/3_fed_hetero_cc.local.yaml \
      --only-family "$fam" \
      --max-parallel-groups 1
done
```

Per-pipeline tunable env vars: `SKILLFL_AGENT_429_RETRIES` (default 20), `SKILLFL_AGENT_429_BASE_SLEEP` (30), `SKILLFL_AGENT_429_MAX_SLEEP` (600) — control how aggressively the runner retries claude-code 429-exhaustion failures before bailing the family.

## Repository layout

```
federate_skill/                              # this repo (~500 KB)
├── README.md
├── setup.sh                                # one-click installer (clones SkillFlow, downloads tasks)
├── pyproject.toml                          # our pip dependencies + skillfl/ packages
├── .env.example                            # API-key template
├── LICENSE                                 # Apache 2.0
├── configs/                                # 4 launch configs (one per paper setting)
│   ├── 1_se_qwen.local.yaml
│   ├── 2_fed_3glm_cc.local.yaml
│   ├── 3_fed_hetero_cc.local.yaml
│   └── 4_fed_hetero_mixed_cli.local.yaml
├── scripts/                                # one-line shell wrappers (read .env, activate venv)
│   ├── _common.sh
│   ├── run_1_se.sh
│   ├── run_2_fed_3glm_cc.sh
│   ├── run_3_fed_hetero_cc.sh
│   └── run_4_fed_hetero_mixed_cli.sh
└── skillfl/                                # the federation adapter (this paper's code)
    ├── harbor_runner.py                    # UserSpec dataclass
    └── skillflow_adapter/
        ├── cli.py                          # federation entry (settings 2-4)
        ├── runner.py                       # FedRunner + per-round loop
        ├── config.py                       # FedConfig dataclass
        ├── harbor_bridge.py                # harbor trial launcher
        ├── patcher_bridge.py               # per-worker patcher routing
        ├── llm_client.py                   # LiteLLM-based call wrapper
        ├── merge.py                        # CloudSkillMerge + RewardWeightedFileMerge
        ├── partitioning.py                 # task → worker assignment
        ├── sync_schedule.py                # when to flush pending patches
        ├── worker_trial.py                 # per-trial result dataclass
        ├── _single_trial.py                # subprocess entry per worker / per task
        ├── merge_skill/SKILL.md            # cloud merger procedure (read by the agent)
        └── task_update_skill/SKILL.md      # task_memory.md updater procedure

# Created by setup.sh, not committed:
├── external/SkillFlow/                     # upstream SkillFlow checkout (libs/ + iter runner)
├── test_tasks/                             # 20 benchmark families (downloaded from HuggingFace)
└── .venv → external/SkillFlow/.venv        # symlinked venv (harbor + SkillFlow + federate_skill)
```

## Citation

If you use this code or benchmark, please cite:

```bibtex
@misc{yang2026federatedskillfederatedlearningagentic,
      title={FederatedSkill: Federated Learning for Agentic Skill Evolution},
      author={Jingbo Yang and Guanyu Yao and Yang Zhang and Ramana Rao Kompella and Gaowen Liu and Shiyu Chang},
      year={2026},
      eprint={2606.03143},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2606.03143},
}
```

## License

Apache 2.0. See [LICENSE](LICENSE).
