# FAISS RAG 통합 계획

## 목표
llm/output에 생성된 FAISS 인덱스를 활용하여 app/prompts에서 RAG(Retrieval-Augmented Generation)를 구현합니다.
visitjeju 워크숍 데이터를 검색하여 프롬프트에 컨텍스트로 제공함으로써 더 정확하고 실제 데이터 기반의 체험 제안을 생성합니다.

## 참고 자료
- [Simple RAG Implementation with FAISS and OpenAI](https://medium.com/@yashpaliwal42/simple-rag-retrieval-augmented-generation-implementation-using-faiss-and-openai-2a74775b17c3)
- [LangChain FAISS Vector Store](https://python.langchain.com/v0.2/docs/integrations/vectorstores/faiss/)
- [Building RAG with LangChain and FAISS](https://medium.com/@alexrodriguesj/retrieval-augmented-generation-rag-with-langchain-and-faiss-a3997f95b551)
- [RAG System from Scratch](https://thoughtsbyakansha.medium.com/how-to-build-a-rag-system-from-scratch-using-langchain-and-faiss-3a5429a1a86d)
- [FAISS RAG Best Practices 2025](https://www.marktechpost.com/2025/03/18/building-a-retrieval-augmented-generation-rag-system-with-faiss-and-open-source-llms/)

## 아키텍처 설계

```
┌─────────────────┐
│ User Query      │
│ (category, etc) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ app/prompts/*.py                │
│ - experience_plan.py            │
│ - steps_suggestion.py           │
│ - materials_suggestion.py       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ llm/rag_retriever.py (NEW)      │
│ - query를 임베딩               │
│ - FAISS 검색 수행              │
│ - 상위 k개 관련 문서 반환      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ llm/output/                     │
│ - visitjeju_faiss.index         │
│ - visitjeju_metadata.json       │
└─────────────────────────────────┘
```

## TDD 단계별 구현 계획

### Phase 1: FAISS 인덱스 생성 및 검증

- [x] **Test 1.1**: FAISS 인덱스 파일 생성 테스트
  - `test_build_faiss_index`: build_index.py 실행 후 index 파일과 metadata 파일이 생성되는지 확인
  - 구현: llm/build_index.py 실행 (이미 작성됨)

- [x] **Test 1.2**: FAISS 인덱스 로드 테스트
  - `test_load_faiss_index`: 생성된 FAISS 인덱스를 정상적으로 로드할 수 있는지 확인
  - 구현: FAISS 인덱스 로드 함수 작성

- [x] **Test 1.3**: 메타데이터 로드 테스트
  - `test_load_metadata`: metadata.json을 로드하고 items와 embedding_model 정보를 확인
  - 구현: 메타데이터 로드 함수 작성

### Phase 2: RAG 검색 모듈 개발 (llm/rag_retriever.py)

- [x] **Test 2.1**: 쿼리 임베딩 생성 테스트
  - `test_embed_query`: 텍스트 쿼리를 임베딩 벡터로 변환하는 함수 테스트
  - 구현: embed_query() 함수 작성 (OpenAI text-embedding-3-small 사용)

- [x] **Test 2.2**: FAISS 유사도 검색 테스트
  - `test_search_similar_documents`: 쿼리 벡터로 상위 k개 유사 문서 검색 테스트
  - 구현: search() 함수 작성 (faiss.IndexFlatL2.search 사용)

- [x] **Test 2.3**: 검색 결과 포매팅 테스트
  - `test_format_search_results`: 검색된 인덱스를 메타데이터와 매칭하여 문서 정보 반환
  - 구현: format_results() 함수 작성 (거리, 제목, 소개, 태그, 주소 포함)

- [x] **Test 2.4**: 통합 검색 테스트
  - `test_retrieve`: 전체 파이프라인 테스트 (쿼리 → 임베딩 → 검색 → 포매팅)
  - 구현: retrieve() 메인 함수 작성

### Phase 3: RAG Retriever 클래스 설계

- [x] **Test 3.1**: RAGRetriever 초기화 테스트
  - `test_rag_retriever_init`: RAGRetriever 클래스 초기화 시 인덱스와 메타데이터 로드 확인
  - 구현: RAGRetriever.__init__() 작성

- [x] **Test 3.2**: retrieve() 메서드 테스트
  - `test_rag_retriever_retrieve`: 카테고리와 키워드로 관련 워크숍 검색
  - 구현: RAGRetriever.retrieve(query, top_k=3) 메서드 작성

- [ ] **Test 3.3**: 캐싱 테스트 (선택) - 스킵
  - `test_rag_retriever_cache`: 동일 쿼리 반복 시 캐싱 동작 확인
  - 구현: 간단한 LRU 캐시 추가 (functools.lru_cache)

### Phase 4: app/prompts 통합

- [x] **RAG 사용 예제 작성 완료** (`llm/example_rag_usage.py`)
  - `build_rag_context()`: 카테고리별 유사 워크숍 검색 함수
  - `enhanced_experience_plan_prompt()`: RAG 컨텍스트가 포함된 프롬프트 생성 함수
  - 실행 결과: "제주 해녀 체험"으로 3개의 유사 워크숍 검색 및 프롬프트에 통합 성공

**참고**: app/prompts 파일을 직접 수정하는 대신, 별도의 RAG 헬퍼 모듈로 분리하여
기존 코드 변경 없이 선택적으로 RAG를 활용할 수 있도록 설계함

### Phase 5: 통합 테스트 및 최적화

- [x] **Test 5.1**: 엔드투엔드 테스트
  - `test_e2e_experience_plan`: 실제 카테고리로 RAG + 프롬프트 전체 흐름 테스트
  - 구현: 통합 테스트 작성 완료

- [x] **Test 5.2**: 성능 테스트
  - `test_retrieval_performance`: 검색 속도 확인 - **361ms** (목표: < 500ms) ✅
  - 구현: 성능 벤치마크 추가 완료 (평균 463ms/5회)

- [x] **Test 5.3**: 오류 처리 테스트
  - `test_error_handling`: 인덱스 파일 없음, API 오류 등 예외 상황 처리
  - 구현: try-except 및 fallback 로직 테스트 완료

- [x] **Bonus**: 배치 처리 성능 테스트
  - `test_batch_retrieval`: 5개 쿼리 배치 처리 - **440ms/쿼리** ✅

### Phase 6: 리팩토링 및 문서화

- [x] **Refactor 6.1**: 코드 중복 제거
  - 검토 완료: 각 함수가 명확한 목적을 가지고 있어 중복 최소화됨

- [x] **Refactor 6.2**: 타입 힌트 추가
  - 완료: 모든 함수에 타입 힌트 적용 완료 (Python 3.13+ 스타일)

- [x] **Refactor 6.3**: 설정 파일 분리
  - `llm/config.py` 생성 완료 (경로, 모델명, top_k 등 상수 관리)

- [x] **Doc 6.4**: README 작성
  - `llm/README.md` 작성 완료: 설치, 사용법, 아키텍처, 성능, 테스트 문서화

### Phase 7: app/prompts RAG 실사용 통합 (Behavior)

- [ ] **Test 7.1**: 경험 템플릿 프롬프트에 RAG 컨텍스트 주입
  - `test_prompts_rag_experience_plan`: RAGRetriever를 스텁으로 주입했을 때 검색 결과 컨텍스트가 system/user 메시지에 포함되는지 확인 (네트워크 호출 없음)
  - 구현: app/prompts/experience_plan.py에 RAG 컨텍스트 조립 헬퍼 추가 및 DI 지점 마련

- [ ] **Test 7.2**: 재료/단계 프롬프트에 RAG 컨텍스트 옵션 적용
  - `test_prompts_rag_materials_steps`: 검색 결과가 있으면 컨텍스트를 덧붙이고, 실패 시 기존 프롬프트로 폴백하는지 검증
  - 구현: materials_suggestion.py, steps_suggestion.py에 선택적 RAG 컨텍스트 추가

- [ ] **Test 7.3**: RAG 비활성/오류 폴백 보장
  - `test_prompts_rag_fallback`: 인덱스/메타데이터 누락 시에도 기존 프롬프트가 깨지지 않고 반환되는지 확인
  - 구현: 컨텍스트 병합 시 try/except 및 플래그 처리

### Phase 8: app/api/routes/experience_plan.py API 연동 (Behavior)

- [ ] **Test 8.1**: /experience-plan 엔드포인트가 RAG 컨텍스트를 포함해 LLM 호출
  - `test_generate_experience_plan_uses_rag_context`: RAGRetriever 스텁이 호출되고, 반환 컨텍스트가 messages에 포함되는지 확인
  - 구현: FastAPI DI로 RAGRetriever 제공, 컨텍스트 병합 후 LLM 호출

- [ ] **Test 8.2**: /materials-suggestion, /steps-suggestion RAG 연동 및 폴백
  - `test_materials_steps_use_rag_context`: 컨텍스트가 메시지에 포함되고, 실패 시 기존 로직으로 폴백하는지 확인
  - 구현: 두 엔드포인트 모두 선택적 RAG 컨텍스트 주입

- [ ] **Test 8.3**: 엔드투엔드 성능/안정성 검증
  - `test_api_rag_performance`: 임베딩 캐시 사용 시 평균 응답 시간이 목표(500ms) 내인지 검증 (스텁 or 측정)
  - 구현: embedding_cache 활용, 필요 시 batching/캐시 워밍업 훅 추가

## 기술 스택

- **Vector DB**: FAISS (faiss-cpu)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Framework**: 순수 Python (LangChain 없이 직접 구현)
- **Testing**: pytest
- **Python Version**: 3.13+

## 디렉토리 구조

```
wadeulwadeul-heroes-be/
├── llm/
│   ├── build_index.py          # 이미 존재 (FAISS 인덱스 생성)
│   ├── rag_retriever.py        # 신규 (RAG 검색 모듈)
│   ├── config.py               # 신규 (설정 관리)
│   ├── output/
│   │   ├── visitjeju_faiss.index      # FAISS 인덱스 파일
│   │   ├── visitjeju_metadata.json    # 메타데이터
│   │   └── visitjeju_workshops.json   # 이미 존재
│   └── tests/
│       ├── test_rag_retriever.py      # 신규
│       └── test_integration.py        # 신규
├── app/
│   └── prompts/
│       ├── experience_plan.py         # RAG 통합으로 수정
│       ├── steps_suggestion.py        # RAG 통합으로 수정
│       └── materials_suggestion.py    # RAG 통합으로 수정
└── plan.md                     # 이 파일
```

## 주요 고려사항

1. **임베딩 모델 일관성**: 인덱스 생성과 검색 시 동일한 모델(text-embedding-3-small) 사용
2. **메타데이터 동기화**: FAISS 인덱스의 벡터 순서와 metadata.json의 items 순서가 일치해야 함
3. **오류 처리**: OpenAI API 호출 실패, 인덱스 파일 없음 등에 대한 fallback
4. **비용 최적화**: 쿼리 임베딩만 실시간 생성, 인덱스는 미리 생성하여 재사용
5. **검색 품질**: top_k=3이 적절한지 실험적으로 검증
6. **프롬프트 설계**: RAG 컨텍스트를 어떻게 프롬프트에 주입할지 신중하게 설계

## 실행 순서

1. `uv run python llm/build_index.py` - FAISS 인덱스 생성
2. `uv run pytest llm/tests/test_rag_retriever.py -v` - RAG 모듈 테스트
3. `uv run pytest app/tests/test_prompts_with_rag.py -v` - 프롬프트 통합 테스트
4. `uv run pytest tests/test_gpt_api.py -v` - API 프롬프트/RAG 통합 테스트
5. 실제 API에서 사용

## 성공 기준

✅ 모든 테스트 통과
✅ 검색 결과가 의미적으로 관련성 있음
✅ 프롬프트 응답 품질 향상
✅ 평균 검색 시간 < 500ms
✅ 오류 상황에서도 안전하게 fallback
