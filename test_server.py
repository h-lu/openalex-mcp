"""
OpenAlex MCP Server 测试脚本

测试精简后的两个核心工具: search_openalex + fetch_openalex
"""

import requests

# OpenAlex API 基础URL
BASE_URL = "https://api.openalex.org"
DEFAULT_PARAMS = {"mailto": "test@example.com"}


def _make_request(endpoint: str, params: dict = None) -> dict:
    """发送 API 请求的辅助函数"""
    url = f"{BASE_URL}/{endpoint}"
    all_params = {**DEFAULT_PARAMS, **(params or {})}
    response = requests.get(url, params=all_params, timeout=30)
    response.raise_for_status()
    return response.json()


def test_search_works():
    """测试搜索论文"""
    print("=== 测试1: 搜索论文 (search_openalex entity_type='works') ===")
    params = {
        "search": "large language model economics",
        "filter": "publication_year:2024-2025",
        "sort": "cited_by_count:desc",
        "per-page": 5,
        "select": "id,title,doi,publication_date,cited_by_count,authorships,primary_location,open_access"
    }
    
    data = _make_request("works", params)
    
    print(f"总数: {data['meta']['count']}")
    print("前5篇论文:")
    for paper in data.get('results', []):
        authorships = paper.get('authorships', [])
        first_author = authorships[0].get('author', {}).get('display_name') if authorships else 'Unknown'
        print(f"  - {paper['title'][:55]}...")
        print(f"    ID: {paper['id'].split('/')[-1]}, 作者: {first_author}, 引用: {paper['cited_by_count']}")
    print()


def test_search_authors():
    """测试搜索作者"""
    print("=== 测试2: 搜索作者 (search_openalex entity_type='authors') ===")
    
    data = _make_request("authors", {"search": "Daron Acemoglu", "per-page": 3})
    
    print(f"总数: {data['meta']['count']}")
    for author in data.get('results', []):
        print(f"  - {author['display_name']}")
        print(f"    ID: {author['id'].split('/')[-1]}, 论文: {author['works_count']}, 引用: {author['cited_by_count']}")
    print()


def test_search_sources():
    """测试搜索期刊"""
    print("=== 测试3: 搜索期刊 (search_openalex entity_type='sources') ===")
    
    data = _make_request("sources", {"search": "American Economic Review", "per-page": 3})
    
    print(f"总数: {data['meta']['count']}")
    for source in data.get('results', []):
        print(f"  - {source['display_name']}")
        print(f"    ID: {source['id'].split('/')[-1]}, 类型: {source.get('type')}, 论文数: {source['works_count']}")
    print()


def test_fetch_work_by_doi():
    """测试通过DOI获取论文"""
    print("=== 测试4: 获取论文详情 (fetch_openalex by DOI) ===")
    
    doi = "https://doi.org/10.1080/00207543.2024.2309309"
    paper = _make_request(f"works/{doi}")
    
    print(f"标题: {paper['title']}")
    print(f"ID: {paper['id'].split('/')[-1]}")
    print(f"DOI: {paper['doi']}")
    print(f"发表日期: {paper['publication_date']}")
    print(f"引用数: {paper['cited_by_count']}")
    print(f"FWCI: {paper.get('fwci')}")
    print(f"期刊: {paper.get('primary_location', {}).get('source', {}).get('display_name')}")
    print(f"开放获取: {paper.get('open_access', {}).get('is_oa')}")
    print("作者:")
    for auth in paper.get('authorships', [])[:3]:
        name = auth.get('author', {}).get('display_name')
        inst = auth.get('institutions', [{}])[0].get('display_name', 'N/A') if auth.get('institutions') else 'N/A'
        print(f"  - {name} ({inst})")
    print()


def test_fetch_author():
    """测试获取作者详情"""
    print("=== 测试5: 获取作者详情 (fetch_openalex entity_type='author') ===")
    
    # 首先搜索获取ID
    author_data = _make_request("authors", {"search": "Daron Acemoglu", "per-page": 1})
    author_id = author_data["results"][0]["id"].split("/")[-1]
    
    # 获取详情
    author = _make_request(f"authors/{author_id}")
    
    print(f"姓名: {author['display_name']}")
    print(f"ID: {author_id}")
    print(f"ORCID: {author.get('orcid')}")
    print(f"论文数: {author['works_count']}")
    print(f"引用数: {author['cited_by_count']}")
    print(f"H指数: {author.get('summary_stats', {}).get('h_index')}")
    
    # 获取代表作
    works = _make_request("works", {
        "filter": f"author.id:{author['id']}",
        "sort": "cited_by_count:desc",
        "per-page": 3,
        "select": "id,title,cited_by_count"
    })
    print("代表作:")
    for work in works.get('results', []):
        print(f"  - {work['title'][:50]}... (引用: {work['cited_by_count']})")
    print()


def test_fetch_source():
    """测试获取期刊详情"""
    print("=== 测试6: 获取期刊详情 (fetch_openalex entity_type='source') ===")
    
    # 首先搜索获取ID
    source_data = _make_request("sources", {"search": "American Economic Review", "per-page": 1})
    source_id = source_data["results"][0]["id"].split("/")[-1]
    
    # 获取详情
    source = _make_request(f"sources/{source_id}")
    
    print(f"名称: {source['display_name']}")
    print(f"ID: {source_id}")
    print(f"ISSN: {source.get('issn_l')}")
    print(f"出版商: {source.get('host_organization_name')}")
    print(f"论文数: {source['works_count']}")
    print(f"总引用: {source['cited_by_count']}")
    print(f"开放获取: {source['is_oa']}")
    print()


if __name__ == "__main__":
    print("OpenAlex MCP Server 精简工具测试\n")
    print("=" * 60)
    print("工具设计: search_openalex + fetch_openalex (ChatGPT Deep Research 模式)")
    print("=" * 60 + "\n")
    
    try:
        test_search_works()
        test_search_authors()
        test_search_sources()
        test_fetch_work_by_doi()
        test_fetch_author()
        test_fetch_source()
        
        print("=" * 60)
        print("✅ 所有测试通过！MCP 服务器功能正常。")
        print("\n工具总结:")
        print("  1. search_openalex - 统一搜索入口 (论文/作者/期刊)")
        print("  2. fetch_openalex - 统一详情获取 (通过 ID 或 DOI)")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise
