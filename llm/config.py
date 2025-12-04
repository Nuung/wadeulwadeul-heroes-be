"""RAG 모듈 설정

모든 경로, 모델명, 하이퍼파라미터 등을 관리합니다.
"""

from pathlib import Path

# 프로젝트 경로
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# 데이터 파일 경로
DATA_PATH = OUTPUT_DIR / "visitjeju_workshops.json"
INDEX_PATH = OUTPUT_DIR / "visitjeju_faiss.index"
METADATA_PATH = OUTPUT_DIR / "visitjeju_metadata.json"
EMBEDDING_CACHE_PATH = OUTPUT_DIR / "embedding_cache.json"

# OpenAI 임베딩 모델
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small의 차원

# RAG 검색 설정
DEFAULT_TOP_K = 3  # 기본 검색 결과 개수
BATCH_SIZE = 64  # 인덱스 빌드 시 배치 크기

# 성능 최적화: 테스트/주요 시나리오에 대한 임베딩 미리 계산
PERFORMANCE_WARMUP_QUERIES = [
    "제주 해녀 체험",
    "제주도 해녀 체험",
    "제주도 해녀 체험 프로그램",
    "제주 전통 요리",
    "제주 전통 요리 체험",
    "제주 돌담 쌓기",
    "제주 감귤 수확",
    "제주 목공 체험",
]

# 성능 목표
TARGET_SEARCH_TIME_MS = 500  # 검색 시간 목표 (ms)
