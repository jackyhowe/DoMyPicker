# -*- coding: utf-8 -*-
"""排序、评分模型与关键词分析。

指标口径（重要，选品结论依赖这些口径）：
- review_count / rating：优先取 listing 自带字段；v3 公开端点通常没有 listing 级
  评论数据，此时回退到所属店铺的 review_count / rating（店铺级），并在输出中标注。
- "热销"：评论数与收藏数的加权分（代理指标，非真实销量）。
- "浏览/加购"：启发式估算分，基于收藏数、评论数与价格区间的加权模型，
  仅用于横向比较，不代表 Etsy 后台真实数据。
"""
import re
from collections import Counter

# ---------- 排序指标 ----------
SORT_MODES = {
    "hot":      "热销（评论×2.5+收藏×0.5，代理指标）",
    "reviews":  "评论数（listing 或店铺级）",
    "rating":   "好评（平均评分，店铺级为主）",
    "favorers": "收藏数",
    "estimate": "浏览/加购估算分（启发式模型）",
}


def get_review_count(listing, shop_map=None):
    """评论数：listing 字段优先，回退店铺级。"""
    v = listing.get("review_count")
    if v is None and shop_map:
        shop = shop_map.get(listing.get("shop_id"))
        if shop:
            v = shop.get("review_count")
    return v or 0


def get_rating(listing, shop_map=None):
    """评分：listing 字段优先，回退店铺级。无评分返回 None。"""
    v = listing.get("rating")
    if v is None and shop_map:
        shop = shop_map.get(listing.get("shop_id"))
        if shop:
            v = shop.get("rating")
    return v if v is not None else None


def price_cent(listing):
    """返回以分为单位的商品价格；数据缺失时返回 None。"""
    price = listing.get("price") or {}
    amount, divisor = price.get("amount"), price.get("divisor")
    if amount is None or not divisor:
        return None
    try:
        return int(amount) / int(divisor) * 100
    except (ValueError, ZeroDivisionError):
        return None


def hot_score(listing, shop_map=None):
    """热销代理分：评论数权重高于收藏数。"""
    return get_review_count(listing, shop_map) * 2.5 + (listing.get("num_favorers") or 0) * 0.5


def estimate_score(listing, shop_map=None):
    """浏览/加购估算分：收藏 + 评论 + 价格带加分（5-50 美元为 Etsy 主流礼品价格带）。"""
    base = (listing.get("num_favorers") or 0) * 1.0 + get_review_count(listing, shop_map) * 3.0
    pc = price_cent(listing)
    if pc is not None:
        if 500 <= pc <= 5000:
            base += 2.0
        elif 100 <= pc < 500:
            base += 1.0
    return round(base, 2)


def sort_listings(listings, sort_mode, shop_map=None):
    """按指标降序排序。rating 排序跳过无评分项；其余指标缺失按 0 计。"""
    mode = (sort_mode or "hot").lower()
    if mode not in SORT_MODES:
        raise ValueError("未知排序方式：%s，可选：%s" % (mode, ", ".join(SORT_MODES)))
    if mode == "hot":
        key = lambda l: hot_score(l, shop_map)
    elif mode == "reviews":
        key = lambda l: get_review_count(l, shop_map)
    elif mode == "rating":
        key = lambda l: get_rating(l, shop_map) or -1
    elif mode == "favorers":
        key = lambda l: l.get("num_favorers") or 0
    else:  # estimate
        key = lambda l: estimate_score(l, shop_map)
    return sorted(listings, key=key, reverse=True)


# ---------- 关键词 / 词频分析 ----------
STOPWORDS = set("""
the a an and or but if then else for of to in on at by with from as is are was were be been
this that these those it its it's i you he she we they my your his her our their me him us them
not no do does did done have has had can could will would should may might must new shop etsy
item items product products handmade custom personalized gift gifts set lot bundle sale
""".split())

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']{1,}")


def tokenize(text):
    """英文分词 + 小写，过滤停用词。"""
    return [w.lower() for w in _WORD_RE.findall(text or "") if w.lower() not in STOPWORDS]


def title_word_frequency(listings, top_n=15):
    """标题高频关键词统计（合并多商品，词频降序）。"""
    words = []
    for l in listings:
        words.extend(tokenize(l.get("title")))
    return Counter(words).most_common(top_n)


def tag_frequency(listings, top_n=20):
    """商品 tags 词频统计（Etsy 每个商品最多 13 个 tag）。"""
    tags = []
    for l in listings:
        tags.extend((t or "").lower() for t in (l.get("tags") or []))
    return Counter(tags).most_common(top_n)


def analyze_listings(listings, shop_map=None):
    """汇总单个商品的可视化分析字段，供表格/CSV 使用。"""
    rows = []
    for l in listings:
        pc = price_cent(l)
        rows.append({
            "listing_id": l.get("listing_id"),
            "title": l.get("title"),
            "shop_name": (shop_map or {}).get(l.get("shop_id"), {}).get("shop_name")
                         if shop_map else None,
            "price_usd": round(pc / 100, 2) if pc is not None else None,
            "num_favorers": l.get("num_favorers") or 0,
            "review_count": get_review_count(l, shop_map),
            "rating": get_rating(l, shop_map),
            "hot_score": round(hot_score(l, shop_map), 1),
            "estimate_score": estimate_score(l, shop_map),
            "url": l.get("url"),
            "tags": "; ".join(l.get("tags") or [])[:120],
        })
    return rows
