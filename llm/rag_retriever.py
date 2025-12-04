"""RAG 검색 모듈

FAISS 인덱스를 사용하여 유사한 문서를 검색하는 기능을 제공합니다.
"""

import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from openai import OpenAI

from llm import config

logger = logging.getLogger(__name__)

client: OpenAI | None = None  # lazy init

EMBEDDING_MODEL = config.EMBEDDING_MODEL
EMBEDDING_CACHE_PATH = config.EMBEDDING_CACHE_PATH

_embedding_cache: dict[str, list[float]] | None = None


def _get_client() -> OpenAI:
    """Lazy OpenAI 클라이언트 생성 (ENV 없으면 명시적 예외)."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        client = OpenAI(api_key=api_key)
    return client


def _load_embedding_cache() -> dict[str, list[float]]:
    """디스크에서 임베딩 캐시 로드 (최초 1회)."""

    global _embedding_cache
    if _embedding_cache is not None:
        return _embedding_cache

    if EMBEDDING_CACHE_PATH.exists():
        with EMBEDDING_CACHE_PATH.open(encoding="utf-8") as f:
            try:
                _embedding_cache = json.load(f)
            except json.JSONDecodeError:
                _embedding_cache = {}
    else:
        _embedding_cache = {}

    return _embedding_cache


def _save_embedding_cache(cache: dict[str, list[float]]) -> None:
    """임베딩 캐시를 디스크에 저장."""

    EMBEDDING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMBEDDING_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False),
        encoding="utf-8",
    )


def _warmup_cache_if_needed() -> None:
    """주요 쿼리 임베딩을 미리 계산하여 검색 시간 단축."""

    warmup_queries = config.PERFORMANCE_WARMUP_QUERIES
    if not warmup_queries:
        return

    cache = _load_embedding_cache()
    missing = [query for query in warmup_queries if query not in cache]
    if not missing:
        return

    response = _get_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=missing,
        encoding_format="float",
    )

    for query, data in zip(missing, response.data, strict=False):
        cache[query] = data.embedding

    with contextlib.suppress(OSError):
        _save_embedding_cache(cache)


def embed_query(query: str) -> np.ndarray:
    """텍스트 쿼리를 임베딩 벡터로 변환

    Args:
        query: 임베딩할 텍스트 쿼리

    Returns:
        (1536,) shape의 float32 numpy 배열
    """
    cache = _load_embedding_cache()
    if query in cache:
        return np.array(cache[query], dtype=np.float32)

    response = _get_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
        encoding_format="float",
    )

    embedding = response.data[0].embedding
    cache[query] = embedding
    with contextlib.suppress(OSError):
        _save_embedding_cache(cache)

    return np.array(embedding, dtype=np.float32)


def search(
    index: faiss.IndexFlatL2, query_vector: np.ndarray, top_k: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """FAISS 인덱스에서 쿼리 벡터와 유사한 문서 검색

    Args:
        index: FAISS IndexFlatL2 인덱스
        query_vector: (1536,) shape의 쿼리 벡터
        top_k: 반환할 상위 문서 개수 (default: 3)

    Returns:
        (distances, indices): 거리와 인덱스 배열, shape은 각각 (1, top_k)
    """
    # 쿼리 벡터를 (1, D) shape으로 변환 (FAISS는 배치 입력 요구)
    if query_vector.ndim == 1:
        query_vector = query_vector.reshape(1, -1)

    # FAISS 검색 수행
    distances, indices = index.search(query_vector, top_k)

    return distances, indices


def format_results(
    distances: np.ndarray, indices: np.ndarray, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """검색 결과를 메타데이터와 매칭하여 포매팅

    Args:
        distances: (1, k) shape의 거리 배열
        indices: (1, k) shape의 인덱스 배열
        items: 메타데이터 items 리스트

    Returns:
        검색 결과 리스트. 각 결과는 distance, title, introduction, alltag, address 포함
    """
    results = []

    # 배치 차원 제거 (1, k) -> (k,)
    distances = distances[0]
    indices = indices[0]

    for distance, idx in zip(distances, indices, strict=False):
        item = items[int(idx)]

        # 필요한 필드 추출
        result = {
            "distance": float(distance),
            "title": item.get("title", ""),
            "introduction": item.get("introduction", ""),
            "alltag": item.get("alltag") or item.get("tag", ""),
            "address": item.get("roadaddress") or item.get("address", ""),
        }

        results.append(result)

    return results


def retrieve(
    query: str,
    top_k: int = 3,
    index_path: str | None = None,
    metadata_path: str | None = None,
) -> list[dict[str, Any]]:
    """전체 RAG 파이프라인 실행

    Args:
        query: 검색할 텍스트 쿼리
        top_k: 반환할 상위 문서 개수 (default: 3)
        index_path: FAISS 인덱스 파일 경로 (default: llm/output/visitjeju_faiss.index)
        metadata_path: 메타데이터 파일 경로 (default: llm/output/visitjeju_metadata.json)

    Returns:
        검색 결과 리스트. 각 결과는 distance, title, introduction, alltag, address 포함
    """
    start_time = time.time()
    logger.info(f"검색 시작 - 쿼리: '{query}', top_k: {top_k}")

    _warmup_cache_if_needed()

    # 기본 경로 설정
    if index_path is None:
        index_path = Path(__file__).parent / "output" / "visitjeju_faiss.index"
    if metadata_path is None:
        metadata_path = Path(__file__).parent / "output" / "visitjeju_metadata.json"

    # 1. 쿼리를 임베딩으로 변환
    query_vector = embed_query(query)

    # 2. FAISS 인덱스 로드
    index = faiss.read_index(str(index_path))

    # 3. 유사 문서 검색
    distances, indices = search(index, query_vector, top_k)

    # 4. 메타데이터 로드
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    # 5. 검색 결과 포매팅
    results = format_results(distances, indices, metadata["items"])

    # 로깅: 검색 완료 및 통계
    elapsed = time.time() - start_time
    distances_list = [r["distance"] for r in results]
    logger.info(
        f"검색 완료 - 소요시간: {elapsed:.3f}s, "
        f"결과수: {len(results)}, "
        f"거리범위: [{min(distances_list):.3f}, {max(distances_list):.3f}]"
    )

    # 로깅: 상위 결과 (DEBUG 레벨)
    for i, result in enumerate(results[:3]):
        logger.debug(
            f"  [{i+1}] distance={result['distance']:.3f}, "
            f"title='{result['title'][:50]}'"
        )

    return results


class RAGRetriever:
    """RAG 검색을 위한 Retriever 클래스

    FAISS 인덱스와 메타데이터를 로드하여 유지하고,
    텍스트 쿼리로 유사한 문서를 검색하는 기능을 제공합니다.
    """

    def __init__(self, index_path: str, metadata_path: str):
        """RAGRetriever 초기화

        Args:
            index_path: FAISS 인덱스 파일 경로
            metadata_path: 메타데이터 JSON 파일 경로
        """
        _warmup_cache_if_needed()

        # FAISS 인덱스 로드
        self.index = faiss.read_index(index_path)

        # 메타데이터 로드
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        self.items = metadata["items"]
        self.embedding_model = metadata["embedding_model"]

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """텍스트 쿼리로 유사한 문서 검색

        Args:
            query: 검색할 텍스트 쿼리
            top_k: 반환할 상위 문서 개수 (default: 3)

        Returns:
            검색 결과 리스트. 각 결과는 distance, title, introduction, alltag, address 포함
        """
        start_time = time.time()
        logger.info(f"검색 시작 - 쿼리: '{query}', top_k: {top_k}")

        # 1. 쿼리를 임베딩으로 변환
        query_vector = embed_query(query)

        # 2. 유사 문서 검색
        distances, indices = search(self.index, query_vector, top_k)

        # 3. 검색 결과 포매팅
        results = format_results(distances, indices, self.items)

        # 로깅: 검색 완료 및 통계
        elapsed = time.time() - start_time
        distances_list = [r["distance"] for r in results]
        logger.info(
            f"검색 완료 - 소요시간: {elapsed:.3f}s, "
            f"결과수: {len(results)}, "
            f"거리범위: [{min(distances_list):.3f}, {max(distances_list):.3f}]"
        )

        # 로깅: 상위 결과 (DEBUG 레벨)
        for i, result in enumerate(results[:3]):
            logger.debug(
                f"  [{i+1}] distance={result['distance']:.3f}, "
                f"title='{result['title'][:50]}'"
            )

        return results
