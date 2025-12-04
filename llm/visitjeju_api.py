import csv
import json
from pathlib import Path
from typing import Any

from curl_cffi import requests

BASE_URL = "https://api.visitjeju.net/vsjApi/contents/searchList"

API_KEY = "05456b7f27d44a13863ed1b5270826b2"

WORKSHOP_KEYWORDS = [
    "체험",
    "공방",
    "공예",
    "도예",
    "도자기",
    "목공",
    "염색",
    "핸드메이드",
    "전통공예",
    "가죽공예",
    "캔들",
]


def fetch_page(
    page: int = 1,
    category: str | None = None,
    locale: str = "kr",
) -> dict[str, Any]:
    """
    비짓제주 SearchList API 한 페이지 호출.
    - 엔드포인트: https://api.visitjeju.net/vsjApi/contents/searchList
    - 쿼리: apiKey, locale, page, (선택)category, (선택)cid
    """
    params = {
        "apiKey": API_KEY,  # ✅ 실제 스펙에서 쓰는 이름
        "locale": locale,
        "page": page,
    }
    if category:
        params["category"] = category

    resp = requests.get(BASE_URL, params=params, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        # 디버깅용: 4xx/5xx일 때 본문 찍어보기
        print("[ERROR] HTTP status:", resp.status_code)
        print("[ERROR] body:", resp.text[:500])
        raise

    # JSON 파싱
    try:
        data = resp.json()
    except Exception:
        print("[ERROR] JSON decode 실패, raw body:")
        print(resp.text[:1000])
        raise

    # result 코드가 있을 수도 있고 없을 수도 있으니, 에러만 대충 체크
    result_code = str(data.get("result", ""))
    result_msg = data.get("resultMessage", "")
    if result_code not in ("", "00", "200", "SUCCESS"):
        print(f"[WARN] API result code: {result_code} / msg={result_msg}")

    return data


def _extract_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    응답에서 items 배열을 꺼낸다.
    - 케이스1: top 레벨에 items[]
    - 케이스2: result.items[] 안에 있을 수도 있음
    """
    if "items" in data and isinstance(data["items"], list):
        return data["items"]
    result = data.get("result")
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        return result["items"]
    return []


def fetch_all_items(
    category: str | None = None,
    locale: str = "kr",
) -> list[dict[str, Any]]:
    """
    pageCount / currentPage 정보를 사용해서
    모든 페이지를 순회하며 items를 전부 가져온다.
    """
    all_items: list[dict[str, Any]] = []

    first = fetch_page(page=1, category=category, locale=locale)

    # 페이지 정보가 없을 수도 있으니 기본값을 안전하게 처리
    total_pages = int(first.get("pageCount") or 1)
    current_page = int(first.get("currentPage") or 1)

    print(f"[INFO] total_pages={total_pages}, first_page={current_page}")

    items = _extract_items(first)
    all_items.extend(items)

    for page in range(current_page + 1, total_pages + 1):
        print(f"[INFO] fetching page {page}/{total_pages}...")
        data = fetch_page(page=page, category=category, locale=locale)
        page_items = _extract_items(data)
        all_items.extend(page_items)

    print(f"[INFO] total raw items fetched = {len(all_items)}")
    return all_items


def is_experience_workshop(item: dict[str, Any]) -> bool:
    """
    '체험·공방' 느낌의 콘텐츠인지 여부를 태그/제목/소개 텍스트를 기준으로 판별.
    실제 응답 JSON 구조에 따라 필드명은 필요시 수정.
    """
    title = item.get("title") or item.get("titleKo") or ""
    tag = item.get("tag") or ""
    alltag = item.get("alltag") or ""
    intro = (
        item.get("introduction")
        or item.get("introductionKo")
        or item.get("sumary")
        or ""
    )

    haystack = " ".join([str(title), str(tag), str(alltag), str(intro)])

    return any(keyword in haystack for keyword in WORKSHOP_KEYWORDS)


def filter_experience_workshops(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [item for item in items if is_experience_workshop(item)]
    print(f"[INFO] workshop-like items = {len(filtered)} / {len(items)}")
    return filtered


# =========================
# 저장용 유틸 함수들
# =========================


def save_to_json(items: list[dict[str, Any]], path: str) -> None:
    """
    결과 리스트를 JSON 파일로 저장.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[INFO] saved {len(items)} items to JSON: {out_path}")


def save_to_csv(items: list[dict[str, Any]], path: str) -> None:
    """
    결과 리스트를 CSV 파일로 저장.
    주요 필드만 골라서 저장.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 실제 응답 보고 필요시 필드명 수정
    fieldnames = [
        "contentsid",
        "title",
        "address",
        "lat",
        "lng",
        "tag",
        "alltag",
        "introduction",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in items:
            row = {
                "contentsid": item.get("contentsid") or item.get("contentid"),
                "title": item.get("title") or item.get("titleKo"),
                "address": item.get("address") or item.get("addressKo"),
                "lat": item.get("repLat") or item.get("latitude"),
                "lng": item.get("repLon") or item.get("longitude"),
                "tag": item.get("tag"),
                "alltag": item.get("alltag"),
                "introduction": (
                    item.get("introduction")
                    or item.get("introductionKo")
                    or item.get("sumary")
                ),
            }
            writer.writerow(row)

    print(f"[INFO] saved {len(items)} items to CSV: {out_path}")


# =========================
# main
# =========================


def main():
    # 아직 체험 카테고리 코드가 확실치 않으면 None으로 두고 전체에서 필터링
    CATEGORY_CODE_FOR_EXPERIENCE = None  # 예: "c1" 같은 값 확인되면 넣기

    # 1) 전체 아이템 수집
    all_items = fetch_all_items(category=CATEGORY_CODE_FOR_EXPERIENCE, locale="kr")

    # 2) 체험·공방으로 필터링
    workshop_items = filter_experience_workshops(all_items)

    # 3) 파일로 저장 (output 디렉터리 기준)
    save_to_json(all_items, "llm/output/visitjeju_all_items.json")
    save_to_csv(all_items, "llm/output/visitjeju_all_items.csv")

    save_to_json(workshop_items, "llm/output/visitjeju_workshops.json")
    save_to_csv(workshop_items, "llm/output/visitjeju_workshops.csv")

    # 4) 샘플 몇 개 콘솔 출력
    print("\n=== SAMPLE RESULTS (first 10 workshops) ===")
    for item in workshop_items[:10]:
        title = item.get("title") or item.get("titleKo")
        address = item.get("address") or item.get("addressKo")
        tag = item.get("tag")
        print(f"- {title} | {address} | tag={tag}")


if __name__ == "__main__":
    main()
