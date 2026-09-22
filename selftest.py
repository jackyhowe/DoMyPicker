# -*- coding: utf-8 -*-
"""离线自检：用样例数据验证排序、评分回退、词频与 CSV 防注入逻辑。
不需要 API key，可随时运行：python selftest.py
"""
import os
import tempfile

import analysis
import report

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s" % name)


# ---- 样例数据（模拟 v3 API 返回）----
LISTINGS = [
    # A：listing 自带评论，高收藏
    {"listing_id": 1, "title": "Vintage Silver Ring Gift Jewelry", "shop_id": 100,
     "num_favorers": 500, "review_count": 80, "rating": 4.9, "tags": ["vintage", "ring", "gift"],
     "price": {"amount": 1900, "divisor": 100, "currency_code": "USD"}},
    # B：listing 无评论字段，回退店铺级（shop 200 有 30 评论）
    {"listing_id": 2, "title": "Handmade Ring Unique Gift", "shop_id": 200,
     "num_favorers": 300, "price": {"amount": 4500, "divisor": 100, "currency_code": "USD"}},
    # C：低收藏低评论（店铺不在 SHOP_MAP 中，评论回退为 0）
    {"listing_id": 3, "title": "Wooden Box Storage", "shop_id": 300,
     "num_favorers": 10, "price": {"amount": 800, "divisor": 100, "currency_code": "USD"}},
]
SHOP_MAP = {
    100: {"shop_id": 100, "shop_name": "RingMaster", "review_count": 999, "rating": 4.5},
    200: {"shop_id": 200, "shop_name": "CraftHub", "review_count": 30, "rating": 4.7},
}


def test_sorting():
    print("== 排序 ==")
    ids = lambda mode: [l["listing_id"] for l in analysis.sort_listings(LISTINGS, mode, SHOP_MAP)]
    check("hot: A > B > C", ids("hot") == [1, 2, 3])
    check("reviews: A(80) > B(30店铺级) > C(0)",
          ids("reviews") == [1, 2, 3] and analysis.get_review_count(LISTINGS[1], SHOP_MAP) == 30)
    check("rating: A(4.9) > B(4.7店铺级) > C(无评分排最后)",
          ids("rating") == [1, 2, 3])
    check("favorers: A(500) > B(300) > C(10)", ids("favorers") == [1, 2, 3])
    # estimate: A = 500 + 80*3 + 2(19美元在5-50区间) = 742; B = 300 + 30*3 + 2(45美元) = 392; C = 10 + 0 + 2(8美元也在5-50区间) = 12
    est = [analysis.estimate_score(l, SHOP_MAP) for l in LISTINGS]
    check("estimate 计算正确", est == [742.0, 392.0, 12.0] and ids("estimate") == [1, 2, 3])


def test_analysis():
    print("== 词频分析 ==")
    tw = dict(analysis.title_word_frequency(LISTINGS, top_n=10))
    check("标题词频：vintage 出现 1 次", tw.get("vintage") == 1)
    check("标题词频：ring 出现 2 次", tw.get("ring") == 2)
    check("标题词频：gift 被停用词过滤（无区分度）", "gift" not in tw)
    tags = dict(analysis.tag_frequency(LISTINGS, top_n=10))
    check("tags 词频：vintage 出现 1 次、ring 出现 1 次", tags.get("vintage") == 1 and tags.get("ring") == 1)
    check("tags 词频：gift 不过滤（tags 是卖家自定义关键词）", tags.get("gift") == 1)


def test_report():
    print("== 输出与 CSV ==")
    rows = analysis.analyze_listings(LISTINGS, SHOP_MAP)
    check("analyze 行数 = 商品数", len(rows) == 3)
    check("shop_name 回填正确", rows[0]["shop_name"] == "RingMaster" and rows[1]["shop_name"] == "CraftHub")
    check("price_usd 换算正确", rows[0]["price_usd"] == 19.0)
    tmp = os.path.join(tempfile.gettempdir(), "etsy_selftest.csv")
    report.export_csv(tmp, rows, [
        ("ID", "listing_id"), ("标题", "title"), ("店铺", "shop_name"),
        ("价格$", "price_usd"), ("收藏", "num_favorers"), ("评论", "review_count"),
        ("评分", "rating"), ("热销分", "hot_score"), ("估算分", "estimate_score"), ("链接", "url")])
    with open(tmp, "rb") as f:
        raw = f.read(3)
        f.seek(0)
        content = f.read().decode("utf-8-sig")
    check("CSV 生成且含 BOM 头（EF BB BF）", raw == b"\xef\xbb\xbf")
    check("CSV 含数据行", content.count("\n") >= 4)
    # 公式注入防护
    evil = [{"listing_id": "=HYPERLINK(\"http://evil\")", "title": "+SUM(A1)", "shop_name": "-1+1",
             "price_usd": None, "num_favorers": 1, "review_count": 1, "rating": 5.0,
             "hot_score": 1.0, "estimate_score": 1.0, "url": "http://x"}]
    tmp2 = os.path.join(tempfile.gettempdir(), "etsy_selftest2.csv")
    report.export_csv(tmp2, evil, [
        ("ID", "listing_id"), ("标题", "title"), ("店铺", "shop_name"), ("价格$", "price_usd"),
        ("收藏", "num_favorers"), ("评论", "review_count"), ("评分", "rating"),
        ("热销分", "hot_score"), ("估算分", "estimate_score"), ("链接", "url")])
    with open(tmp2, "r", encoding="utf-8-sig") as f:
        content2 = f.read()
    check("CSV 公式注入防护（= 加前缀）", content2.count("'=HYPERLINK") == 1 and content2.count("'+SUM") == 1 and content2.count("'-1+1") == 1)
    os.remove(tmp)
    os.remove(tmp2)


if __name__ == "__main__":
    test_sorting()
    test_analysis()
    test_report()
    print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
    raise SystemExit(1 if FAIL else 0)
