"""
LLM 论文筛选与总结模块
使用配置的 LLM 进行相关性打分和中文摘要生成
"""

import json
import re
from typing import Dict, List, Optional

import yaml

from llm_client import LLMClient, format_prompt


class PaperSummarizer:
    """论文筛选与总结器"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompts_path: str = "config/prompts.yaml"
    ):
        self.llm = llm_client or LLMClient()

        with open(prompts_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)

    def score_relevance(self, paper: Dict) -> Dict:
        """
        对单篇论文进行相关性打分

        Returns:
            {"score": int, "reason": str}
        """
        prompt = format_prompt(
            self.prompts['relevance_score'],
            title=paper['title'],
            abstract=paper['abstract']
        )

        try:
            resp = self.llm.chat(prompt, task_type="relevance")

            # 解析 JSON 响应
            # 有时 LLM 会输出 markdown 代码块，需要清理
            resp = self._extract_json(resp)
            result = json.loads(resp)

            # 确保字段存在
            score = int(result.get('score', 0))
            reason = result.get('reason', '无说明')

            return {
                'score': max(0, min(10, score)),  # 限制在 0-10
                'reason': reason
            }

        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试正则提取
            return self._fallback_score_parse(resp)
        except Exception as e:
            print(f"[ERROR] 评分失败: {e}")
            return {'score': 0, 'reason': f'评分出错: {str(e)[:50]}'}

    def summarize(self, paper: Dict) -> str:
        """
        生成中文论文摘要

        Returns:
            Markdown 格式的摘要文本
        """
        prompt = format_prompt(
            self.prompts['summary'],
            title=paper['title'],
            authors=', '.join(paper['authors'][:3]) + (' 等' if len(paper['authors']) > 3 else ''),
            abstract=paper['abstract']
        )

        try:
            summary = self.llm.chat(prompt, task_type="summary")
            return summary.strip()
        except Exception as e:
            print(f"[ERROR] 总结生成失败: {e}")
            return f"**总结生成失败**: {str(e)[:100]}"

    def deep_research(self, paper: Dict) -> str:
        """
        生成深度研究报告（1500字左右）

        Returns:
            Markdown 格式的深度分析
        """
        prompt = format_prompt(
            self.prompts['deep_research'],
            title=paper['title'],
            authors=', '.join(paper['authors'][:3]) + (' 等' if len(paper['authors']) > 3 else ''),
            abstract=paper['abstract']
        )

        try:
            research = self.llm.chat(prompt, task_type="deep_research")
            return research.strip()
        except Exception as e:
            print(f"[ERROR] 深度分析失败: {e}")
            return f"**深度分析失败**: {str(e)[:100]}"

    @staticmethod
    def _extract_json(text: str) -> str:
        """从可能的 markdown 代码块中提取 JSON"""
        # 匹配 ```json ... ``` 或 ``` ... ```
        pattern = r'```(?:json)?\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    @staticmethod
    def _fallback_score_parse(text: str) -> Dict:
        """备用方案：从文本中提取分数"""
        # 尝试找 0-10 的数字
        match = re.search(r'["\']?score["\']?\s*[:=]\s*(\d+)', text)
        if match:
            score = int(match.group(1))
            # 尝试找 reason
            reason_match = re.search(r'["\']?reason["\']?\s*[:=]\s*["\']([^"\']+)', text)
            reason = reason_match.group(1) if reason_match else '解析结果'
            return {'score': score, 'reason': reason}

        # 最后尝试：直接找数字
        numbers = re.findall(r'\b(\d{1,2})\b', text)
        if numbers:
            return {'score': int(numbers[0]), 'reason': text[:100]}

        return {'score': 0, 'reason': '无法解析评分'}


def batch_score_and_summarize(
    papers: List[Dict],
    summarizer: Optional[PaperSummarizer] = None,
    score_threshold: int = 6,
    max_papers: int = 10,
    skip_summary: bool = False
) -> List[Dict]:
    """
    批量打分、筛选并生成摘要

    Args:
        papers: 候选论文列表
        summarizer: PaperSummarizer 实例
        score_threshold: 相关性分数阈值
        max_papers: 最多返回多少篇
        skip_summary: 是否跳过摘要生成（仅打分筛选）

    Returns:
        筛选并排序后的论文列表
    """
    summarizer = summarizer or PaperSummarizer()
    scored_papers = []

    print(f"[INFO] 开始对 {len(papers)} 篇论文进行相关性评分...")

    for i, p in enumerate(papers):
        try:
            result = summarizer.score_relevance(p)
            p.update(result)

            status = "PASS" if result['score'] >= score_threshold else "SKIP"
            print(f"  [{i+1}/{len(papers)}] {status} (score: {result['score']}) {p['title'][:60]}...")

            if result['score'] >= score_threshold:
                scored_papers.append(p)

        except Exception as e:
            print(f"  [ERROR] 评分失败: {e}")
            continue

    # 按分数降序排序
    scored_papers.sort(key=lambda x: x['score'], reverse=True)

    # 限制数量
    if len(scored_papers) > max_papers:
        print(f"[INFO] 筛选 {len(scored_papers)} 篇，保留前 {max_papers} 篇")
        scored_papers = scored_papers[:max_papers]
    else:
        print(f"[INFO] 通过筛选: {len(scored_papers)} 篇")

    # 生成摘要
    if not skip_summary and scored_papers:
        print(f"[INFO] 开始生成中文摘要...")
        for i, p in enumerate(scored_papers):
            try:
                p['summary'] = summarizer.summarize(p)
                print(f"  [{i+1}/{len(scored_papers)}] 摘要完成")
            except Exception as e:
                p['summary'] = f"摘要生成失败: {str(e)[:100]}"

    return scored_papers


if __name__ == "__main__":
    # 测试
    from fetch_arxiv import fetch_recent_papers, load_topics_config

    cfg = load_topics_config()
    papers = fetch_recent_papers(
        keywords=cfg['keywords'][:2],
        categories=cfg['categories'],
        days=1,
        max_per_query=5,
    )

    if papers:
        summarizer = PaperSummarizer()
        results = batch_score_and_summarize(
            papers[:3],
            summarizer=summarizer,
            score_threshold=6
        )
        for r in results:
            print(f"\n{'='*60}")
            print(f"标题: {r['title']}")
            print(f"评分: {r['score']}/10 - {r['reason']}")
            print(f"摘要:\n{r.get('summary', 'N/A')[:300]}...")
