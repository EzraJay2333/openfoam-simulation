# OpenFOAM 仿真技能

[![English](https://img.shields.io/badge/lang-English-blue)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-red)](README_CN.md)

为 Claude Code、Codex、Gemini CLI、Copilot、Cursor 打造的 12 步 OpenFOAM 流体仿真技能 —— 在 Linux/WSL 上规划、搭建、运行、验证和记录 CFD 仿真。专注于流体拓扑/形状优化，内置自学习知识库。

## 快速安装

适用于：**Claude Code** · **Codex (OpenAI)** · **Gemini CLI** · **GitHub Copilot** · **Cursor** · 任何支持 Skills 协议的智能体。

### 通用方式：Git 克隆

选择你的智能体和操作系统，复制命令：

| 智能体 | Linux / macOS | Windows (PowerShell) |
|-------|--------------|---------------------|
| **Claude Code** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git ~/.claude/skills/openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git $env:USERPROFILE\.claude\skills\openfoam-simulation` |
| **Codex (OpenAI)** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git ~/.codex/skills/openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git $env:USERPROFILE\.codex\skills\openfoam-simulation` |
| **Gemini CLI** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git ~/.gemini/skills/openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git $env:USERPROFILE\.gemini\skills\openfoam-simulation` |
| **GitHub Copilot** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git ~/.copilot/skills/openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git $env:USERPROFILE\.copilot\skills\openfoam-simulation` |
| **Cursor** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git .cursor/skills/openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git .cursor\skills\openfoam-simulation` |
| **手动（任意智能体）** | `git clone https://github.com/EzraJay2333/openfoam-simulation.git ./openfoam-simulation` | `git clone https://github.com/EzraJay2333/openfoam-simulation.git .\openfoam-simulation` |

克隆后重启智能体即可生效，无需额外配置。

**💡 一行搞定（Linux/macOS/WSL）：**
```bash
SKILL_DIR="${HOME}/.claude/skills"   # 换成你的智能体路径
git clone https://github.com/EzraJay2333/openfoam-simulation.git "$SKILL_DIR/openfoam-simulation"
```

### 方式 B：.skill 文件（拖拽安装）

1. 下载 [`openfoam-simulation.skill`](https://github.com/EzraJay2333/openfoam-simulation/releases/latest/download/openfoam-simulation.skill)
2. 拖入智能体聊天窗口，或运行安装命令：
   - **Claude Code**: `/install-skill openfoam-simulation.skill`
   - **Codex**: `/skill install openfoam-simulation.skill`
   - **Gemini CLI**: `gemini skill install openfoam-simulation.skill`
   - **Copilot**: `copilot skill install openfoam-simulation.skill`

### 保持更新

```bash
cd <你的技能目录>/openfoam-simulation && git pull
```

一行命令升级到最新版，无需重新下载安装。

## 环境要求

- **操作系统**: Linux (原生) 或 WSL2 (Windows 11)
- **OpenFOAM**: Foundation (openfoam.org) v10+ 或 OpenCFD (openfoam.com) v2206+
- **Python**: 3.x 带 numpy、matplotlib
- **ParaView**: 可选，用于后处理可视化

该技能**绝不**会安装 OpenFOAM 或系统软件 —— 仅检测已有环境。

## 工作流程

| 步骤 | 内容 |
|------|------|
| 1 | 检测环境（WSL/Linux、MPI、OpenFOAM 路径） |
| 2 | 识别 OpenFOAM 发行版、版本、可用求解器 |
| 3 | 采集结构化仿真参数（13 个类别） |
| 4 | 先查本地文档再查在线资料（5 级证据链） |
| 5 | 问题分类（流动状态、物理模型、几何类型、优化类型） |
| 6 | 将求解器能力与问题指纹匹配 |
| 7 | **求解器来源决策**：使用二进制 / 编译 / 修改后编译 / 第三方 |
| 8 | 从知识库匹配或创建工作流 |
| 9 | 构建可复现的案例目录 |
| 10 | **分阶段执行**：语法检查 → 网格 → 烟雾测试 → 原始场 → 伴随 → 算力配置 → 完整运行 |
| 11 | 验证收敛性、守恒性、网格质量、物理合理性 |
| 12 | **记录学习候选**，供未来复用 |

### 预置经典模板

| 模板 | 问题类型 | 优化方法 |
|------|---------|---------|
| `internal-flow-pressure-loss` | 管道/弯管/歧管压降 | 形状 + 拓扑 |
| `external-flow-drag` | 外流气动减阻 | 形状 |
| `duct-shape-optimization` | 弯管/扩散器/喷嘴轮廓 | 形状 + 多目标 |
| `porous-density-topology` | 散热器/流体网络 | 密度拓扑 + 共轭传热 |

### 算力优化

- **MPI 并行**: 推荐核心数、Amdahl 定律加速比估算、分解方法选择
- **GPU**: 可用性检测、CUDA/ROCm 支持、PETSc 集成指导

### 学习系统

每个成功的仿真类型都会记录为 `learned-workflow`。新问题类型以 `experimental`（实验性）状态开始，经过干净重跑 + 用户批准后晋升为 `validated`（已验证），当 OpenFOAM 版本不再兼容时标记为 `deprecated`（已废弃）。

## 文件结构

```
openfoam-simulation/
├── SKILL.md                        # 核心技能（300行，12步状态机）
├── README.md                       # 英文说明
├── README_CN.md                    # 中文说明（本文件）
├── references/
│   ├── intake-schema.md            # 13 节参数规范
│   ├── documentation-policy.md     # 5 级证据优先链
│   ├── solver-selection.md         # 能力驱动求解器匹配
│   ├── solver-compilation.md       # 编译/修改/第三方决策树
│   ├── topology-optimization.md    # 形状 vs 拓扑 vs 水平集分类
│   ├── compute-optimization.md     # MPI/GPU 配置与估算
│   └── validation-and-convergence.md  # 7 阶段验证门控 + ParaView
├── registry/
│   ├── solvers.yaml                # 16 个求解器 + 3 个外部工具
│   ├── problem-types.yaml          # 13 维分类体系
│   └── learned-workflows/          # 自动填充的学习记录
├── templates/                      # 4 个预置经典工作流模板
├── scripts/
│   ├── detect_environment.sh       # 步骤1：WSL/Linux/OpenFOAM 检测
│   ├── inspect_openfoam.sh         # 步骤2：发行版/版本/求解器识别
│   ├── validate_case.sh            # 步骤9：案例结构验证
│   └── scaffold_learning_record.py # 步骤12：学习候选生成
└── evals/
    └── evals.json                  # 6 个测试场景 + 断言
```

## 触发短语

当你提到以下任何内容时，技能会自动激活：
- OpenFOAM、foam、blockMesh、snappyHexMesh
- simpleFoam、pimpleFoam、adjointOptimisationFoam、adjointShapeOptimizationFoam
- CFD 仿真、流体仿真、流场模拟
- 拓扑优化、形状优化、伴随优化
- 压降最小化、减阻、传热模拟
- 网格生成、参数化 CFD 扫描
- "模拟流动"、"优化管道/弯管/通道/机翼/散热器形状"

## 版本

v1.0 — 2026 年 6 月

## 许可证

MIT
