"""
Paper Radar 主入口
每日自动拉取、筛选、总结 arXiv 论文
"""

import os
import sys
from pathlib import Path

import yaml

# 确保 src 目录在路径中
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_arxiv import fetch_recent_papers, load_topics_config
from llm_client import LLMClient
from publish import (generate_notification_content, update_index, write_daily_md,
                     write_deep_research)
from summarize import PaperSummarizer, batch_score_and_summarize


def load_config():
    """加载所有配置"""
    topics_cfg = load_topics_config(PROJECT_ROOT / "config" / "topics.yaml")

    llm_cfg_path = PROJECT_ROOT / "config" / "llm_config.yaml"
    with open(llm_cfg_path, 'r', encoding='utf-8') as f:
        llm_cfg = yaml.safe_load(f)

    return topics_cfg, llm_cfg


def main():
    """主流程"""
    print("=" * 60)
    print("Paper Radar - Daily arXiv Tracker")
    print("=" * 60)

    # 1. 加载配置
    topics_cfg, llm_cfg = load_config()
    filter_cfg = topics_cfg.get('filter', {})

    score_threshold = filter_cfg.get('score_threshold', 6)
    max_papers = filter_cfg.get('max_papers_per_day', 10)
    days = filter_cfg.get('days_lookback', 1)
    max_per_query = filter_cfg.get('max_per_query', 50)

    print(f"\n[CONFIG] 分数阈值: {score_threshold}")
    print(f"[CONFIG] 每日上限: {max_papers}")
    print(f"[CONFIG] 回溯天数: {days}")

    # 2. 初始化 LLM 客户端
    llm = LLMClient(config_path=PROJECT_ROOT / "config" / "llm_config.yaml")
    info = llm.get_info()
    print(f"\n[LLM] 提供商: {info['name']}")
    print(f"[LLM] 模型: {info['model']}")

    summarizer = PaperSummarizer(
        llm_client=llm,
        prompts_path=PROJECT_ROOT / "config" / "prompts.yaml"
    )

    # 3. 从 arXiv 拉取论文
    print(f"\n[1/4] 正在从 arXiv 拉取论文...")
    papers = fetch_recent_papers(
        keywords=topics_cfg['keywords'],
        categories=topics_cfg['categories'],
        days=days,
        max_per_query=max_per_query,
    )

    if not papers:
        print("[INFO] 今日无新论文，流程结束")
        return

    # 4. LLM 筛选 + 生成摘要
    print(f"\n[2/4] 正在进行 LLM 相关性评分...")
    filtered = batch_score_and_summarize(
        papers,
        summarizer=summarizer,
        score_threshold=score_threshold,
        max_papers=max_papers,
        skip_summary=False
    )

    if not filtered:
        print("[INFO] 没有通过筛选的论文，流程结束")
        return

    # 5. 生成 Markdown
    print(f"\n[3/4] 正在生成 Markdown...")
    md_path = write_daily_md(filtered, out_dir=PROJECT_ROOT / "papers")

    # 6. 更新索引
    print(f"\n[4/4] 正在更新索引...")
    update_index(out_dir=PROJECT_ROOT / "papers")

    # 7. 可选：对 Top 3 论文生成深度笔记
    deep_research_enabled = os.environ.get('ENABLE_DEEP_RESEARCH', 'false').lower() == 'true'
    if deep_research_enabled and len(filtered) > 0:
        print(f"\n[BONUS] 生成深度研究报告...")
        for p in filtered[:3]:
            try:
                content = summarizer.deep_research(p)
                write_deep_research(p, content, out_dir=PROJECT_ROOT / "papers")
            except Exception as e:
                print(f"[WARNING] 深度研究失败: {e}")

    # 8. 输出统计
    print(f"\n{'=' * 60}")
    print(f"完成！")
    print(f"  候选论文: {len(papers)}")
    print(f"  通过筛选: {len(filtered)}")
    print(f"  输出文件: {md_path}")
    if filtered:
        print(f"\n  最高分论文:")
        top = filtered[0]
        print(f"    [{top['score']}分] {top['title'][:70]}")

    # 9. 生成推送内容（如有需要）
    notify = os.environ.get('ENABLE_NOTIFY', 'false').lower() == 'true'
    if notify:
        notify_content = generate_notification_content(filtered)
        print(f"\n[NOTIFY] 推送内容已生成（{len(notify_content)} 字符）")
        # 这里可以调用推送函数

    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 流程失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
