"""
arXiv 论文检索模块
支持按关键词和类别筛选，自动去重
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import arxiv
import yaml


def fetch_recent_papers(
    keywords: List[str],
    categories: List[str],
    days: int = 1,
    max_per_query: int = 50,
    delay_seconds: float = 3.0
) -> List[Dict]:
    """
    从 arXiv 获取最近提交的论文

    Args:
        keywords: 关键词列表，每个词单独查询
        categories: arXiv 类别列表
        days: 回溯天数
        max_per_query: 每个查询的最大结果数
        delay_seconds: 请求间隔（避免触发限流）

    Returns:
        去重后的论文列表
    """
    client = arxiv.Client(page_size=100, delay_seconds=delay_seconds)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 构建类别过滤
    cat_filter = " OR ".join([f"cat:{c}" for c in categories])

    all_papers: Dict[str, Dict] = {}

    for kw in keywords:
        # 在标题和摘要中搜索关键词
        query = f'(abs:"{kw}" OR ti:"{kw}") AND ({cat_filter})'

        try:
            search = arxiv.Search(
                query=query,
                max_results=max_per_query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            for r in client.results(search):
                # 超过时间范围则停止
                if r.published < cutoff:
                    break

                # 去重：以 entry_id 为键
                if r.entry_id not in all_papers:
                    all_papers[r.entry_id] = {
                        'title': r.title,
                        'authors': [a.name for a in r.authors],
                        'abstract': r.summary,
                        'url': r.entry_id,
                        'pdf': r.pdf_url,
                        'published': r.published.isoformat(),
                        'published_date': r.published.strftime('%Y-%m-%d'),
                        'primary_category': r.primary_category,
                        'categories': r.categories,
                        'matched_keywords': [kw],
                    }
                else:
                    # 记录额外匹配的关键词
                    if kw not in all_papers[r.entry_id]['matched_keywords']:
                        all_papers[r.entry_id]['matched_keywords'].append(kw)

            # 请求间隔，避免触发限流
            time.sleep(delay_seconds)

        except Exception as e:
            print(f"[WARNING] 查询关键词 '{kw}' 时出错: {e}")
            continue

    papers = list(all_papers.values())
    print(f"[INFO] 从 arXiv 拉取 {len(papers)} 篇候选论文（关键词: {len(keywords)} 个）")
    return papers


def load_topics_config(path: str = "config/topics.yaml") -> Dict:
    """加载主题配置"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_fetch():
    """测试拉取功能"""
    cfg = load_topics_config()
    papers = fetch_recent_papers(
        keywords=cfg['keywords'][:3],  # 只测试前3个关键词
        categories=cfg['categories'],
        days=1,
        max_per_query=10,
    )
    for p in papers[:3]:
        print(f"- {p['title'][:80]}... ({p['published_date']})")
    print(f"\n总计: {len(papers)} 篇")


if __name__ == "__main__":
    test_fetch()
