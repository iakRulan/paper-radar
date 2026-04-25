# Paper Radar

每日自动追踪 arXiv 上与 Ryan 研究方向相关的最新论文，使用 LLM 进行相关性打分并生成中文摘要。

## 研究方向

- 联邦学习（异构客户端、通信效率、事件触发）
- 多智能体世界模型（3D Gaussian Splatting、Dreamer、扩散世界模型）
- 端到端具身控制（VLA、Diffusion Policy）
- 自动驾驶 V2X 协同感知与规划
- 多机器人协同操控

## 工作流程

```
GitHub Actions (每天 UTC 0:00)
    |
    v
arXiv API 检索最近 24h 论文
    |
    v
LLM 相关性打分 (0-10)
    |
    v
筛选 >= 6 分的论文，最多 10 篇
    |
    v
LLM 生成中文摘要
    |
    v
生成 Markdown + 更新索引
    |
    v
自动 commit 到本仓库
```

## 项目结构

```
.
|-- .github/workflows/daily.yml    # 定时任务配置
|-- src/
|   |-- main.py                    # 主入口
|   |-- fetch_arxiv.py             # arXiv 检索
|   |-- llm_client.py              # LLM 客户端（多提供商）
|   |-- summarize.py               # 打分 + 摘要
|   |-- publish.py                 # Markdown 生成 + 索引
|-- config/
|   |-- topics.yaml                # 关键词 + 类别配置
|   |-- prompts.yaml               # LLM prompt 模板
|   |-- llm_config.yaml            # LLM 提供商配置
|-- papers/                        # 输出目录
|   |-- 2026/
|   |   |-- 04/
|   |   |   |-- 2026-04-25.md     # 每日论文
|   |   |   |-- 2026-04-26.md
|   |-- README.md                  # 自动更新的索引
|-- requirements.txt
|-- README.md                      # 本文件
```

## LLM 配置

支持多种 LLM 提供商，修改 `config/llm_config.yaml` 中的 `active_provider` 即可切换：

| 提供商 | 配置项 | 环境变量 |
|--------|--------|----------|
| **DeepSeek** (默认) | `deepseek` | `DEEPSEEK_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic Claude | `claude` | `ANTHROPIC_API_KEY` |
| SiliconFlow | `siliconflow` | `SILICONFLOW_API_KEY` |
| 自定义 | `custom` | `CUSTOM_API_KEY` + `CUSTOM_BASE_URL` |

### 设置 API Key

1. 打开仓库 Settings -> Secrets and variables -> Actions
2. 点击 `New repository secret`
3. 添加对应的 API Key（如 `DEEPSEEK_API_KEY`）

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/Ryan-coder/paper-radar.git
cd paper-radar

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置环境变量
export DEEPSEEK_API_KEY="your-api-key"
# 或切换到其他模型
export OPENAI_API_KEY="your-api-key"

# 5. 运行
python src/main.py
```

## 手动触发

进入 Actions 页面 -> 选择 `Daily Paper Radar` -> 点击 `Run workflow`。

## 自定义配置

### 修改关键词

编辑 `config/topics.yaml`：

```yaml
keywords:
  - federated learning
  - 3D Gaussian Splatting
  # 添加你的关键词...

categories:
  - cs.RO
  - cs.CV
  # 添加 arXiv 类别...

filter:
  score_threshold: 6      # 相关性阈值
  max_papers_per_day: 10  # 每日上限
```

### 切换 LLM 模型

编辑 `config/llm_config.yaml`：

```yaml
# 切换提供商
active_provider: openai  # deepseek / claude / siliconflow / custom

# 或只切换模型
providers:
  deepseek:
    default_model: deepseek-reasoner  # 切换模型
```

## 归档

查看历史论文：

- [papers/README.md](papers/README.md) - 完整索引
- [papers/2026/04/](papers/2026/04/) - 按月归档

## License

MIT
