import json
import os
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from llm import config

# ---------- 경로 & 설정 ----------
DATA_PATH = Path("llm/output/visitjeju_workshops.json")  # 이미 저장해 둔 파일
INDEX_PATH = Path("llm/output/visitjeju_faiss.index")  # FAISS 인덱스 저장 위치
# 메타데이터(원본 items) 저장 위치
META_PATH = Path("llm/output/visitjeju_metadata.json")
CACHE_PATH = config.EMBEDDING_CACHE_PATH

EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI 임베딩 모델
_client: OpenAI | None = None
# ---------------------------------


def _get_client() -> OpenAI:
    """Lazy OpenAI 클라이언트 생성 (ENV 미설정 시 명시적 예외)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required to build index")
        _client = OpenAI(api_key=api_key)
    return _client
# ---------------------------------


def load_items():
    """visitjeju_workshops.json 로드"""
    with DATA_PATH.open(encoding="utf-8") as f:
        items = json.load(f)
    assert isinstance(items, list), "JSON 최상위가 list 여야 합니다."
    return items


def build_text(item: dict) -> str:
    """
    한 item을 하나의 '문서 문자열'로 합치는 함수.
    (임베딩 입력으로 사용)
    """
    title = item.get("title", "")
    intro = item.get("introduction", "")
    alltag = item.get("alltag") or item.get("tag", "")
    addr = item.get("roadaddress") or item.get("address", "")

    parts = [
        f"이름: {title}",
        f"소개: {intro}",
        f"태그: {alltag}",
        f"주소: {addr}",
    ]
    # 빈 문자열 제거 후 합치기
    return "\n".join(p for p in parts if p.strip())


def embed_texts(texts, batch_size: int = 64) -> np.ndarray:
    """
    여러 개의 텍스트를 배치로 나눠 임베딩 → (N, D) float32 numpy 배열로 반환.
    """
    vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # OpenAI 공식 예제와 동일한 방식으로 embeddings.create 사용 :contentReference[oaicite:8]{index=8}
        resp = _get_client().embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            encoding_format="float",  # float 벡터로 받기
        )

        for d in resp.data:
            vectors.append(d.embedding)

    # FAISS는 float32를 요구합니다. :contentReference[oaicite:9]{index=9}
    return np.array(vectors, dtype="float32")


def build_and_save_index(embeddings: np.ndarray, items: list):
    """
    FAISS IndexFlatL2 인덱스를 생성하고, 인덱스 + 원본 items를 디스크에 저장
    """
    # embeddings shape: (N, D)
    _, d = embeddings.shape
    print(f"[INFO] embeddings shape = {embeddings.shape}")

    # 1) IndexFlatL2 생성 (L2 거리 기반 정확 검색) :contentReference[oaicite:11]{index=11}
    index = faiss.IndexFlatL2(d)
    assert index.is_trained
    index.add(embeddings)  # 내부적으로 데이터를 복사해서 저장

    # 2) 인덱스 파일로 저장
    faiss.write_index(index, str(INDEX_PATH))

    # 3) 원본 items + 모델 정보도 함께 저장 (RAG 시 메타 활용)
    meta = {
        "embedding_model": EMBEDDING_MODEL,
        "items": items,  # 순서 중요: 0번째 벡터 ↔ 0번째 item
    }
    META_PATH.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[INFO] Saved FAISS index to {INDEX_PATH}")
    print(f"[INFO] Saved metadata to {META_PATH}")


def prewarm_embedding_cache() -> None:
    """주요 쿼리 임베딩을 미리 계산해 캐시에 저장하여 검색 속도 향상."""

    warmup_queries = config.PERFORMANCE_WARMUP_QUERIES
    if not warmup_queries:
        return

    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    else:
        cache = {}

    queries_to_embed = [q for q in warmup_queries if q not in cache]
    if not queries_to_embed:
        return

    resp = _get_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=queries_to_embed,
        encoding_format="float",
    )

    for query, data in zip(queries_to_embed, resp.data, strict=False):
        cache[query] = data.embedding

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[INFO] Saved warmup embedding cache to {CACHE_PATH}")


def main():
    items = load_items()
    texts = [build_text(it) for it in items]

    print(f"[INFO] #items = {len(items)}")
    embeddings = embed_texts(texts, batch_size=64)
    build_and_save_index(embeddings, items)
    prewarm_embedding_cache()


if __name__ == "__main__":
    main()
