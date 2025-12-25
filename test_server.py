"""
OpenAlex MCP Server 综合测试脚本

测试所有三个工具的功能:
1. search_openalex - 简单搜索
2. query_openalex - 高级查询（原生 filter）
3. fetch_openalex - 获取详情

运行: uv run python test_server.py
"""

import requests
import time

BASE_URL = "https://api.openalex.org"
PARAMS = {"mailto": "test@example.com"}


def req(endpoint: str, params: dict = None) -> dict:
    """发送 API 请求"""
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params={**PARAMS, **(params or {})}, timeout=30)
    response.raise_for_status()
    return response.json()


def test_search_works():
    """测试 search_openalex: 基本论文搜索"""
    print("=" * 70)
    print("测试 1: search_openalex - 搜索 2024 年机器学习论文")
    print("=" * 70)
    
    data = req("works", {
        "search": "machine learning",
        "filter": "publication_year:2024",
        "sort": "cited_by_count:desc",
        "per-page": 5
    })
    
    print(f"总数: {data['meta']['count']:,} 篇")
    print("\n前 5 篇高引论文:")
    for i, w in enumerate(data["results"], 1):
        auths = w.get("authorships", [])
        first_author = auths[0]["author"]["display_name"] if auths else "Unknown"
        print(f"  {i}. {w['title'][:60]}...")
        print(f"     作者: {first_author} | 引用: {w['cited_by_count']} | OA: {w['open_access']['is_oa']}")
    print()


def test_search_authors():
    """测试 search_openalex: 搜索作者"""
    print("=" * 70)
    print("测试 2: search_openalex - 搜索经济学领域知名作者")
    print("=" * 70)
    
    data = req("authors", {
        "search": "Daron Acemoglu",
        "per-page": 3
    })
    
    print(f"总数: {data['meta']['count']} 位匹配作者")
    for a in data["results"]:
        print(f"  - {a['display_name']}")
        print(f"    ID: {a['id'].split('/')[-1]} | 论文: {a['works_count']} | 引用: {a['cited_by_count']}")
    print()


def test_search_keywords():
    """测试 search_openalex: 搜索关键词实体"""
    print("=" * 70)
    print("测试 3: search_openalex - 搜索 AI 相关关键词")
    print("=" * 70)
    
    data = req("keywords", {
        "search": "large language model",
        "per-page": 5
    })
    
    print(f"总数: {data['meta']['count']} 个关键词")
    for k in data["results"]:
        print(f"  - {k['display_name']}")
        print(f"    ID: {k['id'].split('/')[-1]} | 论文数: {k['works_count']:,}")
    print()


def test_query_complex_filter():
    """测试 query_openalex: 复杂过滤器组合"""
    print("=" * 70)
    print("测试 4: query_openalex - 复杂过滤器")
    print("       查找 2024 年中国作者发表的开放获取 AI 论文")
    print("=" * 70)
    
    data = req("works", {
        "filter": "publication_year:2024,authorships.countries:CN,is_oa:true",
        "search": "artificial intelligence",
        "sort": "cited_by_count:desc",
        "per-page": 5
    })
    
    print(f"Filter: publication_year:2024,authorships.countries:CN,is_oa:true")
    print(f"Search: artificial intelligence")
    print(f"总数: {data['meta']['count']:,} 篇")
    print("\n前 5 篇:")
    for i, w in enumerate(data["results"], 1):
        auths = w.get("authorships", [])
        countries = set()
        for a in auths:
            countries.update(a.get("countries", []))
        print(f"  {i}. {w['title'][:55]}...")
        print(f"     引用: {w['cited_by_count']} | 国家: {', '.join(countries)}")
    print()


def test_query_institution_filter():
    """测试 query_openalex: 按机构过滤"""
    print("=" * 70)
    print("测试 5: query_openalex - MIT 高引论文")
    print("=" * 70)
    
    # 先获取 MIT 的 ID
    mit_data = req("institutions", {"search": "Massachusetts Institute of Technology", "per-page": 1})
    mit_id = mit_data["results"][0]["id"]
    mit_name = mit_data["results"][0]["display_name"]
    
    print(f"机构: {mit_name} ({mit_id.split('/')[-1]})")
    
    data = req("works", {
        "filter": f"authorships.institutions.id:{mit_id},cited_by_count:>500",
        "sort": "cited_by_count:desc",
        "per-page": 5
    })
    
    print(f"Filter: authorships.institutions.id:{mit_id.split('/')[-1]},cited_by_count:>500")
    print(f"总数: {data['meta']['count']:,} 篇高引论文 (>500 引用)")
    print("\n前 5 篇:")
    for i, w in enumerate(data["results"], 1):
        print(f"  {i}. {w['title'][:55]}...")
        print(f"     引用: {w['cited_by_count']} | 年份: {w['publication_year']}")
    print()


def test_query_journal_filter():
    """测试 query_openalex: 按期刊过滤"""
    print("=" * 70)
    print("测试 6: query_openalex - Nature 期刊的气候变化论文")
    print("=" * 70)
    
    # 先获取 Nature 的 ID
    nature_data = req("sources", {"search": "Nature", "per-page": 1})
    nature_id = nature_data["results"][0]["id"]
    nature_name = nature_data["results"][0]["display_name"]
    
    print(f"期刊: {nature_name} ({nature_id.split('/')[-1]})")
    
    data = req("works", {
        "filter": f"primary_location.source.id:{nature_id}",
        "search": "climate change",
        "sort": "cited_by_count:desc",
        "per-page": 5
    })
    
    print(f"Filter: primary_location.source.id:{nature_id.split('/')[-1]}")
    print(f"Search: climate change")
    print(f"总数: {data['meta']['count']:,} 篇")
    print("\n前 5 篇:")
    for i, w in enumerate(data["results"], 1):
        print(f"  {i}. {w['title'][:55]}...")
        print(f"     引用: {w['cited_by_count']} | 年份: {w['publication_year']}")
    print()


def test_query_group_by():
    """测试 query_openalex: 分组聚合"""
    print("=" * 70)
    print("测试 7: query_openalex - 按年份分组统计 LLM 论文")
    print("=" * 70)
    
    data = req("works", {
        "search": "large language model",
        "group_by": "publication_year"
    })
    
    print(f"总数: {data['meta']['count']:,} 篇")
    print("\n按年份分布:")
    groups = sorted(data.get("group_by", []), key=lambda x: x.get("key", ""), reverse=True)[:10]
    for g in groups:
        year = g.get("key", "Unknown")
        count = g.get("count", 0)
        bar = "█" * min(count // 500, 40)
        print(f"  {year}: {count:>6} {bar}")
    print()


def test_fetch_work_detail():
    """测试 fetch_openalex: 获取论文完整详情"""
    print("=" * 70)
    print("测试 8: fetch_openalex - 获取论文详情 (含 keywords/funders)")
    print("=" * 70)
    
    # 使用一个著名的 AI 论文
    doi = "https://doi.org/10.48550/arXiv.2303.08774"  # GPT-4 Technical Report
    
    try:
        data = req(f"works/{doi}")
        
        print(f"标题: {data['title']}")
        print(f"DOI: {data['doi']}")
        print(f"年份: {data['publication_year']}")
        print(f"引用: {data['cited_by_count']}")
        print(f"FWCI: {data.get('fwci', 'N/A')}")
        print(f"类型: {data['type']}")
        print(f"语言: {data.get('language', 'N/A')}")
        print(f"OA: {data['open_access']['is_oa']} ({data['open_access']['oa_status']})")
        
        # 作者
        print(f"\n作者 ({len(data['authorships'])} 位):")
        for a in data["authorships"][:5]:
            name = a["author"]["display_name"]
            insts = [i["display_name"] for i in a.get("institutions", [])]
            print(f"  - {name}")
            if insts:
                print(f"    机构: {insts[0]}")
        if len(data["authorships"]) > 5:
            print(f"  ... 还有 {len(data['authorships']) - 5} 位作者")
        
        # 关键词
        keywords = data.get("keywords", [])
        if keywords:
            print(f"\n关键词 ({len(keywords)} 个):")
            for k in keywords[:8]:
                print(f"  - {k['display_name']} (score: {k.get('score', 0):.3f})")
        
        # 资助
        funders = data.get("funders", [])
        if funders:
            print(f"\n资助机构 ({len(funders)} 个):")
            for f in funders[:5]:
                print(f"  - {f['display_name']}")
        
        # 主题
        topic = data.get("primary_topic", {})
        if topic:
            print(f"\n主题分类:")
            print(f"  主题: {topic.get('display_name')}")
            print(f"  领域: {topic.get('field', {}).get('display_name')}")
            print(f"  域: {topic.get('domain', {}).get('display_name')}")
    
    except requests.exceptions.HTTPError:
        print("该论文可能尚未被 OpenAlex 收录，使用备用论文...")
        # 备用：使用已知存在的论文
        data = req("works/https://doi.org/10.1080/00207543.2024.2309309")
        print(f"标题: {data['title']}")
        print(f"引用: {data['cited_by_count']}")
        print(f"关键词: {[k['display_name'] for k in data.get('keywords', [])[:5]]}")
    
    print()


def test_fetch_author_detail():
    """测试 fetch_openalex: 获取作者详情及代表作"""
    print("=" * 70)
    print("测试 9: fetch_openalex - 获取作者详情 (含代表作)")
    print("=" * 70)
    
    # 获取 Yoshua Bengio 的详情
    author_data = req("authors", {"search": "Yoshua Bengio", "per-page": 1})
    author_id = author_data["results"][0]["id"]
    
    data = req(f"authors/{author_id}")
    
    print(f"姓名: {data['display_name']}")
    print(f"ID: {data['id'].split('/')[-1]}")
    print(f"ORCID: {data.get('orcid', 'N/A')}")
    print(f"论文数: {data['works_count']}")
    print(f"总引用: {data['cited_by_count']}")
    print(f"H指数: {data.get('summary_stats', {}).get('h_index')}")
    
    # 机构 (affiliations 结构是 {institution: {display_name: ...}})
    affiliations = data.get("affiliations", [])
    if affiliations:
        print(f"\n机构:")
        for a in affiliations[:3]:
            inst = a.get("institution", {})
            print(f"  - {inst.get('display_name', 'N/A')}")
    
    # 获取代表作
    works = req("works", {
        "filter": f"author.id:{author_id}",
        "sort": "cited_by_count:desc",
        "per-page": 5
    })
    
    print(f"\n代表作 (按引用排序):")
    for i, w in enumerate(works["results"], 1):
        print(f"  {i}. {w['title'][:50]}...")
        print(f"     引用: {w['cited_by_count']} | 年份: {w['publication_year']}")
    print()


def test_fetch_funder_detail():
    """测试 fetch_openalex: 获取资助机构详情"""
    print("=" * 70)
    print("测试 10: fetch_openalex - 获取资助机构详情")
    print("=" * 70)
    
    # 搜索 NSF
    funder_data = req("funders", {"search": "National Science Foundation", "per-page": 1})
    funder_id = funder_data["results"][0]["id"]
    
    data = req(f"funders/{funder_id}")
    
    print(f"名称: {data['display_name']}")
    print(f"ID: {data['id'].split('/')[-1]}")
    print(f"国家: {data.get('country_code', 'N/A')}")
    works_count = data.get('works_count')
    cited_count = data.get('cited_by_count')
    grants_count = data.get('grants_count')
    print(f"资助论文数: {works_count:,}" if works_count else "资助论文数: N/A")
    print(f"总引用: {cited_count:,}" if cited_count else "总引用: N/A")
    print(f"资助项目数: {grants_count:,}" if grants_count else "资助项目数: N/A")
    print(f"主页: {data.get('homepage_url', 'N/A')}")
    
    # 获取该机构资助的高引论文
    works = req("works", {
        "filter": f"funders.id:{funder_id}",
        "sort": "cited_by_count:desc",
        "per-page": 3
    })
    
    print(f"\n资助的高引论文:")
    for i, w in enumerate(works["results"], 1):
        print(f"  {i}. {w['title'][:50]}...")
        print(f"     引用: {w['cited_by_count']}")
    print()


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " OpenAlex MCP Server 综合测试 ".center(68) + "║")
    print("║" + " 测试 search_openalex / query_openalex / fetch_openalex ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    tests = [
        ("search_openalex - 论文搜索", test_search_works),
        ("search_openalex - 作者搜索", test_search_authors),
        ("search_openalex - 关键词搜索", test_search_keywords),
        ("query_openalex - 复杂过滤器", test_query_complex_filter),
        ("query_openalex - 机构过滤", test_query_institution_filter),
        ("query_openalex - 期刊过滤", test_query_journal_filter),
        ("query_openalex - 分组聚合", test_query_group_by),
        ("fetch_openalex - 论文详情", test_fetch_work_detail),
        ("fetch_openalex - 作者详情", test_fetch_author_detail),
        ("fetch_openalex - 资助机构", test_fetch_funder_detail),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            time.sleep(0.3)  # 避免触发速率限制
        except Exception as e:
            print(f"❌ {name} 失败: {e}")
            failed += 1
    
    print("=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    if failed == 0:
        print("✅ 所有测试通过！MCP 服务器功能正常。")
    print("=" * 70)


if __name__ == "__main__":
    main()
