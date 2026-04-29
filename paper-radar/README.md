# Paper Radar

每日自动追踪 arXiv 最新论文，通过 LLM 打分筛选并生成中文摘要，结果自动归档到仓库。

## 功能

### 1. 论文检索

从 arXiv 自动拉取最近 24 小时（可配置）内发布的论文：

- 支持多关键词组合搜索（当前配置 15 个关键词）
- 支持多 arXiv 分类并行检索（cs.RO / cs.CV / cs.LG / cs.MA 等 8 个类别）
- 自动去重，跨关键词命中时合并记录
- 通过 `days_lookback` 控制回溯天数，`max_per_query` 控制单次查询上限

修改检索范围：编辑 `config/topics.yaml`

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
  days_lookback: 1       # 回溯天数
  max_per_query: 50      # 每个查询最大结果数
```

---

### 2. LLM 相关性打分

对每篇论文调用 LLM 打分（0–10），只保留高于阈值的论文：

- 打分基于论文标题 + 摘要，低温度（0.2）保证结果稳定
- 返回 JSON 格式：`{"score": 7, "reason": "..."}`，含一句话打分理由
- 支持配置分数阈值与每日输出上限

修改筛选参数：编辑 `config/topics.yaml`

```yaml
filter:
  score_threshold: 6      # 达到此分数才输出，默认 6
  max_papers_per_day: 10  # 每日最多保留论文数，默认 10
```

---

### 3. 中文摘要生成

对筛选后的论文逐篇生成结构化中文摘要，包含四部分：

1. **核心贡献** — 2–3 句，说明论文解决了什么问题
2. **技术方法** — 3–5 句，说明具体技术路线
3. **与研究的关联** — 结合具体研究方向的针对性分析
4. **值得关注的点** — 1 句，提炼最值得跟进的内容

---

### 4. 深度研究报告（可选）

对当日评分最高的前 3 篇论文生成约 1500 字的深度笔记：

- 研究背景与动机
- 核心方法与技术细节
- 实验设计与结果分析
- 与已有工作的对比
- 对当前研究的具体启发
- 值得改进的方向与相关论文推荐

启用方式：

```bash
export ENABLE_DEEP_RESEARCH=true
python src/main.py
```

深度报告保存在 `papers/YYYY/MM/deep/` 目录下。

---

### 5. Markdown 归档与索引

每日生成一个 Markdown 文件，记录所有筛选论文的完整信息：

- 论文标题、作者、发布时间
- arXiv 链接与 PDF 直链
- 所属分类与命中关键词
- LLM 相关性得分与理由
- 中文摘要（结构化四部分）

文件自动归档到 `papers/YYYY/MM/YYYY-MM-DD.md`，同时更新 `papers/README.md` 索引（按年/月分组，含每日论文数统计）。

---

### 6. 多 LLM 提供商支持

通过统一接口支持多个 LLM 提供商，切换无需改代码：

| 提供商 | 配置项 | 环境变量 | 可用模型 |
|--------|--------|----------|----------|
| **DeepSeek**（默认） | `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat, deepseek-reasoner |
| OpenAI | `openai` | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini, o1-mini |
| Anthropic Claude | `claude` | `ANTHROPIC_API_KEY` | claude-3-5-sonnet, claude-3-5-haiku |
| SiliconFlow | `siliconflow` | `SILICONFLOW_API_KEY` | DeepSeek-V3, Qwen 等 |
| 自定义 | `custom` | `CUSTOM_API_KEY` | 任意 OpenAI 兼容接口 |

切换提供商：编辑 `config/llm_config.yaml`

```yaml
active_provider: openai  # 改为目标提供商名称

providers:
  deepseek:
    default_model: deepseek-reasoner  # 也可只切换模型
```

---

### 7. 自动化运行（GitHub Actions）

内置 GitHub Actions 工作流，每天 UTC 0:00 自动执行完整流程，结果自动 commit 到仓库。

**配置步骤：**

1. 进入仓库 `Settings → Secrets and variables → Actions`
2. 新建 Secret，名称与值对应所选提供商（如 `DEEPSEEK_API_KEY`）
3. 推送代码后工作流自动生效

**手动触发：** Actions 页面 → `Daily Paper Radar` → `Run workflow`

---

### 8. 推送通知（可选）

生成结构化推送内容（论文列表 + 摘要），可对接 Webhook 或其他推送渠道。

启用方式：

```bash
export ENABLE_NOTIFY=true
python src/main.py
```

---

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/iakrulan/paper-radar.git
cd paper-radar

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置 API Key
export DEEPSEEK_API_KEY="your-api-key"

# 5. 运行
python src/main.py
```

---

## 项目结构

```
.
├── .github/workflows/daily.yml   # 定时任务配置
├── src/
│   ├── main.py                   # 主入口与流程编排
│   ├── fetch_arxiv.py            # arXiv 检索
│   ├── llm_client.py             # LLM 多提供商统一客户端
│   ├── summarize.py              # 打分 + 摘要 + 深度报告
│   └── publish.py                # Markdown 生成与索引维护
├── config/
│   ├── topics.yaml               # 关键词、类别、筛选参数
│   ├── llm_config.yaml           # LLM 提供商与模型配置
│   └── prompts.yaml              # LLM Prompt 模板
├── papers/                       # 输出目录（自动生成）
│   ├── README.md                 # 自动更新的归档索引
│   └── YYYY/MM/
│       ├── YYYY-MM-DD.md         # 每日论文报告
│       └── deep/                 # 深度研究报告（可选）
└── requirements.txt
```

---

## License

MIT
