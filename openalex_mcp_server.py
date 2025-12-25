"""
OpenAlex MCP Server - 使用 FastMCP 构建的学术论文搜索工具

提供给 AI Agent (如 Cursor, Claude Desktop) 使用的 MCP 工具，
用于搜索和获取 OpenAlex 上的学术论文信息。

最佳实践 (2025.12):
- 工具数量精简: 使用 search + fetch 模式（参考 ChatGPT Deep Research）
- 清晰的工具职责: 每个工具有明确单一的用途
- 类型提示完整: 所有函数都有完整的类型注解

运行方式:
    1. stdio 模式 (用于 Cursor/Claude Desktop): python openalex_mcp_server.py
    2. http 模式 (用于调试): python openalex_mcp_server.py --http
    3. 使用 fastmcp CLI: fastmcp run openalex_mcp_server.py
"""

import datetime
import os
import requests
from typing import Optional, Literal
from fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP(
    name="OpenAlex",
    instructions="""
    OpenAlex 学术论文搜索工具。提供两个核心工具：
    
    1. search_openalex - 搜索论文、作者或期刊
    2. fetch_openalex - 获取具体实体的详细信息
    
    典型工作流:
    1. 使用 search_openalex 搜索，获取 ID 列表
    2. 使用 fetch_openalex 获取感兴趣项目的详细信息
    
    数据来源: OpenAlex (https://openalex.org) - 包含 2.5 亿+ 学术论文
    """
)

# OpenAlex API 基础URL
BASE_URL = "https://api.openalex.org"

# 添加邮箱以提高速率限制 (1次/秒 -> 10次/秒)
# 通过环境变量 OPENALEX_EMAIL 配置，可在 mcp.json 的 env 字段中设置
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "openalex-mcp@example.com")
DEFAULT_PARAMS = {"mailto": OPENALEX_EMAIL}


def _make_request(endpoint: str, params: dict | None = None) -> dict:
    """发送 API 请求的辅助函数"""
    url = f"{BASE_URL}/{endpoint}"
    all_params = {**DEFAULT_PARAMS, **(params or {})}
    response = requests.get(url, params=all_params, timeout=30)
    response.raise_for_status()
    return response.json()


def _format_paper_brief(paper: dict) -> dict:
    """格式化论文简要信息"""
    authorships = paper.get("authorships", [])
    first_author = authorships[0].get("author", {}).get("display_name") if authorships else "Unknown"
    
    primary_location = paper.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    
    return {
        "id": paper.get("id", "").replace("https://openalex.org/", ""),
        "title": paper.get("title"),
        "doi": paper.get("doi"),
        "publication_date": paper.get("publication_date"),
        "cited_by_count": paper.get("cited_by_count"),
        "first_author": first_author,
        "author_count": len(authorships),
        "journal": source.get("display_name"),
        "is_oa": paper.get("open_access", {}).get("is_oa"),
    }


def _format_paper_full(paper: dict) -> dict:
    """格式化论文完整信息"""
    # 提取作者信息
    authors = []
    for authorship in paper.get("authorships", []):
        authors.append({
            "name": authorship.get("author", {}).get("display_name"),
            "orcid": authorship.get("author", {}).get("orcid"),
            "position": authorship.get("author_position"),
            "institutions": [
                inst.get("display_name") 
                for inst in authorship.get("institutions", [])
            ],
            "countries": authorship.get("countries", [])
        })
    
    # 提取期刊信息
    primary_location = paper.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    
    # 提取主题信息
    primary_topic = paper.get("primary_topic", {}) or {}
    
    # 提取关键词
    keywords = [kw.get("display_name") for kw in paper.get("keywords", [])[:8]]
    
    return {
        "id": paper.get("id", "").replace("https://openalex.org/", ""),
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "publication_date": paper.get("publication_date"),
        "publication_year": paper.get("publication_year"),
        "language": paper.get("language"),
        "type": paper.get("type"),
        "cited_by_count": paper.get("cited_by_count"),
        "fwci": paper.get("fwci"),  # Field-Weighted Citation Impact
        "is_top_1_percent": paper.get("citation_normalized_percentile", {}).get("is_in_top_1_percent"),
        "journal": source.get("display_name"),
        "publisher": source.get("host_organization_name"),
        "volume": paper.get("biblio", {}).get("volume"),
        "issue": paper.get("biblio", {}).get("issue"),
        "pages": f"{paper.get('biblio', {}).get('first_page', '')}-{paper.get('biblio', {}).get('last_page', '')}".strip("-"),
        "authors": authors,
        "is_oa": paper.get("open_access", {}).get("is_oa"),
        "oa_status": paper.get("open_access", {}).get("oa_status"),
        "pdf_url": primary_location.get("pdf_url"),
        "primary_topic": primary_topic.get("display_name"),
        "field": primary_topic.get("field", {}).get("display_name"),
        "domain": primary_topic.get("domain", {}).get("display_name"),
        "keywords": keywords,
        "referenced_works_count": paper.get("referenced_works_count"),
        "abstract": _reconstruct_abstract(paper.get("abstract_inverted_index")),
    }


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """从倒排索引重建摘要文本"""
    if not inverted_index:
        return None
    
    # 重建摘要
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    
    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


def _format_author(author: dict) -> dict:
    """格式化作者信息"""
    return {
        "id": author.get("id", "").replace("https://openalex.org/", ""),
        "name": author.get("display_name"),
        "orcid": author.get("orcid"),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "h_index": author.get("summary_stats", {}).get("h_index"),
        "affiliations": [
            inst.get("display_name") 
            for inst in author.get("affiliations", [])[:3]
        ],
        "topics": [
            topic.get("display_name")
            for topic in author.get("topics", [])[:5]
        ],
    }


def _format_journal(source: dict) -> dict:
    """格式化期刊信息"""
    return {
        "id": source.get("id", "").replace("https://openalex.org/", ""),
        "name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
        "type": source.get("type"),
        "works_count": source.get("works_count"),
        "cited_by_count": source.get("cited_by_count"),
        "is_oa": source.get("is_oa"),
        "homepage_url": source.get("homepage_url"),
    }


@mcp.tool(
    name="search_openalex",
    description="搜索学术论文、作者或期刊。返回匹配结果的 ID 列表和摘要信息。",
    tags={"search", "openalex", "academic"}
)
def search_openalex(
    query: str,
    entity_type: Literal["works", "authors", "sources"] = "works",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sort_by: Literal["cited_by_count", "publication_date", "relevance"] = "cited_by_count",
    limit: int = 10
) -> dict:
    """
    在 OpenAlex 中搜索学术实体。
    
    Args:
        query: 搜索关键词，例如 "large language model economics" 或作者名 "Daron Acemoglu"
        entity_type: 搜索类型 - "works"(论文), "authors"(作者), "sources"(期刊)
        year_from: 起始年份过滤（仅对论文有效），例如 2020
        year_to: 结束年份过滤（仅对论文有效），例如 2025
        sort_by: 排序方式 - "cited_by_count"(引用数), "publication_date"(发表日期), "relevance"(相关度)
        limit: 返回结果数量，默认10，最大50
    
    Returns:
        包含搜索结果的字典:
        - total_count: 总匹配数
        - results: 结果列表，每项包含 id 和基本信息
        
    使用示例:
        搜索论文: search_openalex("machine learning finance", entity_type="works", year_from=2024)
        搜索作者: search_openalex("Daron Acemoglu", entity_type="authors")
        搜索期刊: search_openalex("American Economic Review", entity_type="sources")
    """
    params = {
        "search": query,
        "per-page": min(limit, 50),
    }
    
    # 对论文搜索应用年份过滤
    if entity_type == "works":
        params["select"] = "id,title,doi,publication_date,cited_by_count,authorships,primary_location,open_access"
        
        current_year = datetime.datetime.now().year
        filters = []
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:{year_from}-{current_year}")
        elif year_to:
            filters.append(f"publication_year:1900-{year_to}")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        # 排序
        if sort_by == "cited_by_count":
            params["sort"] = "cited_by_count:desc"
        elif sort_by == "publication_date":
            params["sort"] = "publication_date:desc"
    
    try:
        data = _make_request(entity_type, params)
        
        results = []
        for item in data.get("results", []):
            if entity_type == "works":
                results.append(_format_paper_brief(item))
            elif entity_type == "authors":
                results.append({
                    "id": item.get("id", "").replace("https://openalex.org/", ""),
                    "name": item.get("display_name"),
                    "works_count": item.get("works_count"),
                    "cited_by_count": item.get("cited_by_count"),
                })
            elif entity_type == "sources":
                results.append({
                    "id": item.get("id", "").replace("https://openalex.org/", ""),
                    "name": item.get("display_name"),
                    "type": item.get("type"),
                    "works_count": item.get("works_count"),
                    "publisher": item.get("host_organization_name"),
                })
        
        return {
            "total_count": data.get("meta", {}).get("count"),
            "results": results
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"搜索失败: {str(e)}"}


@mcp.tool(
    name="fetch_openalex",
    description="获取论文、作者或期刊的详细信息。支持通过 ID 或 DOI 查询。",
    tags={"fetch", "openalex", "academic"}
)
def fetch_openalex(
    identifier: str,
    entity_type: Literal["work", "author", "source"] = "work",
    include_works: bool = False
) -> dict:
    """
    获取 OpenAlex 实体的详细信息。
    
    Args:
        identifier: 实体标识符，可以是:
            - OpenAlex ID: 如 "W4391403992", "A5012301204", "S23254222"
            - DOI: 如 "10.1080/00207543.2024.2309309" (仅对论文有效)
            - 完整 URL: 如 "https://openalex.org/W4391403992"
        entity_type: 实体类型 - "work"(论文), "author"(作者), "source"(期刊)
        include_works: 对于作者/期刊，是否包含其代表作品列表（最多5篇）
    
    Returns:
        实体的详细信息
        
    使用示例:
        获取论文: fetch_openalex("10.1080/00207543.2024.2309309", entity_type="work")
        获取作者: fetch_openalex("A5012301204", entity_type="author", include_works=True)
        获取期刊: fetch_openalex("S23254222", entity_type="source")
    """
    # 规范化标识符
    id_clean = identifier.strip()
    
    # 移除 URL 前缀
    if id_clean.startswith("https://openalex.org/"):
        id_clean = id_clean.replace("https://openalex.org/", "")
    
    # 对于 DOI，添加前缀
    if entity_type == "work" and (id_clean.startswith("10.") or "doi.org" in id_clean):
        if not id_clean.startswith("https://doi.org/"):
            if id_clean.startswith("doi.org/"):
                id_clean = f"https://{id_clean}"
            else:
                id_clean = f"https://doi.org/{id_clean}"
    
    # 确定 API 端点
    endpoint_map = {"work": "works", "author": "authors", "source": "sources"}
    endpoint = endpoint_map.get(entity_type, "works")
    
    try:
        data = _make_request(f"{endpoint}/{id_clean}")
        
        if entity_type == "work":
            result = _format_paper_full(data)
        elif entity_type == "author":
            result = _format_author(data)
            
            # 获取作者的代表作品
            if include_works:
                works_data = _make_request("works", {
                    "filter": f"author.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "id,title,doi,publication_date,cited_by_count,primary_location"
                })
                result["top_works"] = [
                    {
                        "id": p.get("id", "").replace("https://openalex.org/", ""),
                        "title": p.get("title"),
                        "doi": p.get("doi"),
                        "cited_by_count": p.get("cited_by_count"),
                        "journal": (p.get("primary_location", {}) or {}).get("source", {}).get("display_name"),
                    }
                    for p in works_data.get("results", [])
                ]
        elif entity_type == "source":
            result = _format_journal(data)
            
            # 获取期刊的高引论文
            if include_works:
                works_data = _make_request("works", {
                    "filter": f"primary_location.source.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "id,title,doi,publication_date,cited_by_count,authorships"
                })
                result["top_works"] = [
                    {
                        "id": p.get("id", "").replace("https://openalex.org/", ""),
                        "title": p.get("title"),
                        "doi": p.get("doi"),
                        "cited_by_count": p.get("cited_by_count"),
                        "first_author": p.get("authorships", [{}])[0].get("author", {}).get("display_name") if p.get("authorships") else None,
                    }
                    for p in works_data.get("results", [])
                ]
        else:
            result = data
        
        return result
        
    except requests.exceptions.HTTPError as e:
        return {"error": f"获取失败: {str(e)}"}


def main():
    """入口点函数，用于 uvx 和 pip install 后直接运行"""
    import sys
    
    # 检查是否使用 HTTP 模式
    if "--http" in sys.argv:
        print("Starting OpenAlex MCP Server in HTTP mode on port 8000...")
        mcp.run(transport="http", port=8000)
    else:
        # 默认使用 stdio 模式（用于 Cursor/Claude Desktop）
        mcp.run()


if __name__ == "__main__":
    main()
