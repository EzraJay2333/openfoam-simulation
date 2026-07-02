# 本机拓扑优化能力补充教程

## 1. 当前基线与缺口

截至 2026-07-02，本机 WSL 环境的已核实基线为：

| 项目 | 当前状态 | 用途 |
|---|---|---|
| OpenFOAM Foundation 13 | `/home/ezrajay/OpenFOAM/OpenFOAM-13` | 通用 primal、CHT primal、legacy 压损阻塞优化 |
| `adjointShapeOptimisationFoam` | 已有二进制 | 仅限总压损失的 legacy blockage-field 优化 |
| `porousSimpleFoam` | 已有二进制 | 等温多孔介质 primal，可由外部优化器驱动 |
| `foamMultiRun` / `chtMultiRegionFoam` | 已有 | 多区域流固传热 primal |
| MPI / `wmake` | 已有 | 并行运行和用户目录编译 |
| NumPy / SciPy | 已有 | 基础外部标量优化 |
| OpenCFD `adjointOptimisationFoam` | 缺失 | 现代等温孔隙率/Level-set 拓扑 |
| DAKOTA | 缺失 | 文件接口、参数研究及多目标驱动 |
| pyOptSparse | 缺失 | 稀疏约束优化及可选 NSGA2/IPOPT 后端 |

当前硬件为 16 个逻辑 CPU、约 7.5 GiB RAM、RTX 3060 Laptop 6 GiB。
现有 OpenFOAM 路线主要受内存而不是 GPU 限制。二维和粗网格三维原型可用；
工程级三维拓扑建议至少 32 GiB RAM，三维 CHT 或高分辨率 Pareto 批量计算建议
64 GiB。上述容量是规划建议，最终以网格规模实测峰值内存为准。

## 2. 推荐的软件组合

不要混用 Foundation 和 OpenCFD 的字典、库路径或同一个终端环境。推荐保留
Foundation 13，并在独立目录并行安装 OpenCFD v2512：

| 工作负载 | 推荐后端 |
|---|---|
| 固定总压损失的快速 legacy 原型 | Foundation 13 `adjointShapeOptimisationFoam` |
| 一般等温压降/均匀性拓扑 | OpenCFD v2512 `adjointOptimisationFoam` |
| CHT 传热拓扑、最高温度约束 | Foundation/OpenCFD thermal primal + 外部优化器，或自定义热伴随 |
| 加权和或 epsilon-constraint | SciPy、DAKOTA 或 pyOptSparse 外部驱动 |
| Pareto 前沿 | DAKOTA 或 pyOptSparse/NSGA2；不能用一次加权和代替 |

OpenCFD v2512 是稳定基线；v2312 是本 Skill 声明的原生等温拓扑最低版本。
v2606 发布较新，使用前应重新检查其教程、字典和回归结果。

## 3. 并行安装 OpenCFD v2512（WSL Ubuntu）

以下命令需要用户在 WSL 中主动执行。Skill 不会自动运行 `sudo` 或修改
`~/.bashrc`。

```bash
# 1. 确认 Ubuntu 版本；v2512 官方提供 Ubuntu 22.04/24.04 包
lsb_release -a

# 2. 添加 OpenCFD 官方 Debian/Ubuntu 软件源
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
sudo apt update

# 3. 安装前先确认包确实来自 OpenCFD 仓库
apt-cache policy openfoam2512-default

# 4. 安装独立的 OpenCFD v2512 包
sudo apt install openfoam2512-default
```

官方入口：

- <https://www.openfoam.com/download/openfoam-installation-on-linux>
- <https://www.openfoam.com/news/main-news/openfoam-v2512>

不要把两个发行版同时写入 shell 启动文件。每个新终端只激活一个环境：

```bash
# Foundation 13 会话
bash --noprofile --norc
source /home/ezrajay/OpenFOAM/OpenFOAM-13/etc/bashrc
printf 'family=Foundation root=%s version=%s\n' "$WM_PROJECT_DIR" "$WM_PROJECT_VERSION"

# 或在另一个全新终端中启动 OpenCFD v2512 会话
bash --noprofile --norc
source /usr/lib/openfoam/openfoam2512/etc/bashrc
printf 'family=OpenCFD root=%s version=%s\n' "$WM_PROJECT_DIR" "$WM_PROJECT_VERSION"
```

如果软件包给出的安装路径不同，以 `dpkg -L openfoam2512-default | grep '/etc/bashrc$'`
的结果为准，不要猜路径。

### v2512 安装验收

```bash
command -v adjointOptimisationFoam
adjointOptimisationFoam -help

find "$FOAM_TUTORIALS/incompressible/adjointOptimisationFoam" \
  -maxdepth 4 -type d -iname '*topology*' -o -iname '*porosity*'

find "$WM_PROJECT_DIR/src" \
  -path '*adjointOptimisation*' \
  \( -iname '*topO*' -o -iname '*levelSet*' \) | head -50
```

只有同时找到可执行文件、同版本 topology 教程和设计变量源码后，Skill 才能把
该路线标记为 `native`。OpenCFD 官方 v2312 手册明确把 `topO`、`dynamicTopO`
和 `levelSet` 列为拓扑设计变量：
<https://www.openfoam.com/documentation/files/adjointOptimisationFoamManual_v2312.pdf>。

## 4. 建立隔离的外部优化 Python 环境

本机已有 SciPy，但仍建议建立项目专用虚拟环境，避免系统 Python 和 CFD 驱动脚本
互相污染：

```bash
python3 -m venv "$HOME/venvs/openfoam-opt"
source "$HOME/venvs/openfoam-opt/bin/activate"
python -m pip install --upgrade pip
python -m pip install numpy scipy matplotlib pandas pyyaml jsonschema

python - <<'PY'
import numpy, scipy
from scipy import optimize
print('numpy', numpy.__version__)
print('scipy', scipy.__version__)
print('minimize available:', callable(optimize.minimize))
PY
```

SciPy 适合：

- 少量几何参数；
- 加权和或 epsilon-constraint 原型；
- 小设计维度的有限差分验证。

SciPy 本身不是 OpenFOAM 耦合层。仍需驱动程序负责复制案例、写入设计变量、运行
primal、读取目标/约束、保存日志和 `run_manifest.json`。

官方接口：<https://docs.scipy.org/doc/scipy/reference/optimize.html>。

## 5. 可选安装 pyOptSparse

需要稀疏约束、IPOPT 或 NSGA2 时，优先使用隔离的 Conda 环境：

```bash
conda create -n openfoam-pyoptsparse -c conda-forge pyoptsparse
conda activate openfoam-pyoptsparse
python - <<'PY'
import pyoptsparse
print(pyoptsparse.__version__)
PY
```

若没有 Conda，不要直接污染 OpenFOAM 自带 Python。按 pyOptSparse 官方文档在独立
目录从源码构建，并准备 C/Fortran 编译器、Python headers；NSGA2 还需要 SWIG。

官方安装文档：
<https://mdolab-pyoptsparse.readthedocs-hosted.com/en/stable/install.html>。

## 6. 可选安装 DAKOTA

DAKOTA 更适合文件接口、参数研究、代理模型和多目标任务。官方 Linux 二进制主要
针对列出的 RHEL 平台；WSL Ubuntu 上应先验证兼容性，不兼容时再考虑源码构建。

```bash
# 下载并解压官方归档后，将路径替换为实际安装目录
export DAKOTA_ROOT="$HOME/opt/Dakota"
export PATH="$DAKOTA_ROOT/bin:$PATH"

command -v dakota
dakota --version
```

不要在验证成功前把路径写入 `~/.bashrc`。官方教程：
<https://snl-dakota.github.io/docs/6.23.0/users/setupdakota.html>。

## 7. CHT 拓扑优化耦合流程

当前 Foundation 13 只能提供 thermal primal。外部优化驱动至少应实现：

1. 将只读基准案例复制到独立迭代目录；
2. 写入参数化几何、cell zone、阻力或材料插值字段；
3. 运行 `blockMesh`/`snappyHexMesh` 和 `checkMesh`；
4. 用 `foamMultiRun` 或版本对应的 `chtMultiRegionFoam` 运行 CHT primal；
5. 提取总压损失、最高温度、热阻、换热量和体积分数；
6. 失败时返回有界惩罚值，并保留完整日志；
7. 更新设计变量并记录目标、约束、文件哈希和求解器版本；
8. 最终几何重新网格，并执行独立 primal 复算和网格独立性检查。

低维参数可使用有限差分。高维单元级拓扑若仍使用有限差分，每次梯度需要近似
`N+1` 次 primal，通常不可接受；此时应开发并验证热伴随，或把设计空间降维。

## 8. 多目标策略选择

| 策略 | 适用情况 | 必须记录 |
|---|---|---|
| 加权和 | 快速得到单一折中解 | 目标归一化、权重、量纲 |
| epsilon-constraint | 一个主目标、其他指标有明确上限 | epsilon 值及可行性 |
| Pareto/NSGA2 | 需要完整权衡前沿 | 种群、随机种子、终止准则、非支配解集 |

压降和温度量纲、数量级不同，禁止直接相加。至少先用 baseline 值归一化，例如：

```text
J = w_p * (DeltaP / DeltaP_baseline)
  + w_T * ((Tmax - Tin) / (Tmax_baseline - Tin))
```

这仍然只是一个标量折中解，不是 Pareto 前沿。

## 9. 最终验收清单

```bash
# Foundation 会话
source /home/ezrajay/OpenFOAM/OpenFOAM-13/etc/bashrc
command -v adjointShapeOptimisationFoam porousSimpleFoam foamMultiRun mpirun wmake

# OpenCFD 会话（安装后）
source /usr/lib/openfoam/openfoam2512/etc/bashrc
command -v adjointOptimisationFoam
adjointOptimisationFoam -help

# 外部优化环境
source "$HOME/venvs/openfoam-opt/bin/activate"
python -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)"
command -v dakota || true
python -c "import pyoptsparse" 2>/dev/null || true
```

随后分别运行三个最小案例：等温压降拓扑、CHT primal 外部驱动单次评价、双目标
标量化或 Pareto smoke test。三者不能共用未经版本验证的字典。
