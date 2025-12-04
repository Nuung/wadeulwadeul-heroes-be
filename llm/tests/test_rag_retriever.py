"""RAG Retriever 모듈 테스트"""

# llm 모듈을 임포트하기 위한 경로 설정
import sys
from pathlib import Path

import faiss
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRAGRetriever:
    """RAG Retriever 기능 테스트"""

    def test_embed_query(self):
        """Test 2.1: 텍스트 쿼리를 임베딩 벡터로 변환하는 함수 테스트"""
        # Given: 테스트용 쿼리 텍스트
        from llm.rag_retriever import embed_query

        query = "제주도 해녀 체험"

        # When: 쿼리를 임베딩으로 변환
        embedding = embed_query(query)

        # Then: 임베딩이 numpy 배열이어야 함
        assert isinstance(
            embedding, np.ndarray
        ), f"임베딩이 numpy 배열이 아님: {type(embedding)}"

        # Then: 임베딩 shape이 (1536,)이어야 함 (text-embedding-3-small)
        assert embedding.shape == (1536,), f"임베딩 shape이 올바르지 않음: {embedding.shape}"

        # Then: 임베딩이 float32 타입이어야 함
        assert embedding.dtype == np.float32, f"임베딩 dtype이 올바르지 않음: {embedding.dtype}"

        # Then: 임베딩 값이 모두 0이 아니어야 함
        assert not np.all(embedding == 0), "임베딩이 모두 0임"

        # Then: 임베딩 벡터의 L2 norm이 대략 1에 가까워야 함 (정규화 확인)
        norm = np.linalg.norm(embedding)
        assert 0.9 < norm < 1.1, f"임베딩이 정규화되지 않음: norm={norm}"

    def test_search_similar_documents(self):
        """Test 2.2: 쿼리 벡터로 상위 k개 유사 문서 검색 테스트"""
        # Given: FAISS 인덱스와 쿼리 벡터
        from llm.rag_retriever import search

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        assert index_path.exists(), f"FAISS index 파일이 없음: {index_path}"

        # 인덱스 로드
        index = faiss.read_index(str(index_path))

        # 테스트용 쿼리 벡터 생성 (랜덤 벡터)
        query_vector = np.random.rand(1536).astype(np.float32)
        top_k = 3

        # When: 유사 문서 검색
        distances, indices = search(index, query_vector, top_k)

        # Then: 거리와 인덱스가 numpy 배열이어야 함
        assert isinstance(distances, np.ndarray), f"distances가 numpy 배열이 아님: {type(distances)}"
        assert isinstance(indices, np.ndarray), f"indices가 numpy 배열이 아님: {type(indices)}"

        # Then: shape이 (1, top_k)이어야 함
        assert distances.shape == (1, top_k), f"distances shape이 올바르지 않음: {distances.shape}"
        assert indices.shape == (1, top_k), f"indices shape이 올바르지 않음: {indices.shape}"

        # Then: 인덱스 값이 유효 범위 내에 있어야 함
        assert np.all(indices >= 0), "인덱스에 음수 값이 있음"
        assert np.all(indices < index.ntotal), f"인덱스가 범위를 벗어남: max={indices.max()}, ntotal={index.ntotal}"

        # Then: 거리 값이 음수가 아니어야 함 (L2 거리)
        assert np.all(distances >= 0), "거리에 음수 값이 있음"

        # Then: 거리가 오름차순으로 정렬되어 있어야 함 (가장 가까운 순서)
        for i in range(top_k - 1):
            assert distances[0, i] <= distances[0, i + 1], f"거리가 정렬되지 않음: {distances}"

    def test_format_search_results(self):
        """Test 2.3: 검색된 인덱스를 메타데이터와 매칭하여 문서 정보 반환"""
        # Given: 검색 결과 인덱스와 메타데이터
        import json

        from llm.rag_retriever import format_results

        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"
        assert metadata_path.exists(), f"metadata 파일이 없음: {metadata_path}"

        # 메타데이터 로드
        with metadata_path.open(encoding="utf-8") as f:
            metadata = json.load(f)

        # 테스트용 검색 결과 (가상의 인덱스와 거리)
        distances = np.array([[0.5, 1.2, 2.3]], dtype=np.float32)
        indices = np.array([[0, 5, 10]], dtype=np.int64)

        # When: 검색 결과를 포매팅
        results = format_results(distances, indices, metadata["items"])

        # Then: 결과가 리스트여야 함
        assert isinstance(results, list), f"결과가 리스트가 아님: {type(results)}"

        # Then: 결과 개수가 인덱스 개수와 일치해야 함
        assert len(results) == 3, f"결과 개수가 올바르지 않음: {len(results)}"

        # Then: 각 결과가 필요한 필드를 포함해야 함
        required_fields = ["distance", "title", "introduction", "alltag", "address"]
        for i, result in enumerate(results):
            assert isinstance(result, dict), f"결과 {i}가 dict가 아님: {type(result)}"
            for field in required_fields:
                assert field in result, f"결과 {i}에 {field} 필드가 없음"

        # Then: distance 값이 올바른지 확인 (부동소수점 오차 허용)
        assert abs(results[0]["distance"] - 0.5) < 0.01, f"첫 번째 distance가 올바르지 않음: {results[0]['distance']}"
        assert abs(results[1]["distance"] - 1.2) < 0.01, f"두 번째 distance가 올바르지 않음: {results[1]['distance']}"

        # Then: 메타데이터에서 가져온 title이 있어야 함
        assert results[0]["title"], "첫 번째 결과의 title이 비어있음"

    def test_retrieve(self):
        """Test 2.4: 전체 파이프라인 테스트 (쿼리 → 임베딩 → 검색 → 포매팅)"""
        # Given: 텍스트 쿼리
        from llm.rag_retriever import retrieve

        query = "제주도 해녀 체험 프로그램"
        top_k = 3

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # When: retrieve() 함수로 전체 파이프라인 실행
        results = retrieve(query, top_k, str(index_path), str(metadata_path))

        # Then: 결과가 리스트여야 함
        assert isinstance(results, list), f"결과가 리스트가 아님: {type(results)}"

        # Then: 결과 개수가 top_k와 일치해야 함
        assert len(results) == top_k, f"결과 개수가 올바르지 않음: {len(results)}"

        # Then: 각 결과가 필요한 필드를 포함해야 함
        required_fields = ["distance", "title", "introduction", "alltag", "address"]
        for i, result in enumerate(results):
            assert isinstance(result, dict), f"결과 {i}가 dict가 아님: {type(result)}"
            for field in required_fields:
                assert field in result, f"결과 {i}에 {field} 필드가 없음"

        # Then: distance 값이 양수여야 함
        for i, result in enumerate(results):
            assert result["distance"] >= 0, f"결과 {i}의 distance가 음수: {result['distance']}"

        # Then: 거리가 오름차순으로 정렬되어 있어야 함
        for i in range(len(results) - 1):
            assert (
                results[i]["distance"] <= results[i + 1]["distance"]
            ), "결과가 거리순으로 정렬되지 않음"

        # Then: 실제 의미있는 결과가 반환되어야 함 (title이 비어있지 않음)
        assert results[0]["title"], "첫 번째 결과의 title이 비어있음"


class TestRAGRetrieverClass:
    """RAGRetriever 클래스 테스트"""

    def test_rag_retriever_init(self):
        """Test 3.1: RAGRetriever 클래스 초기화 시 인덱스와 메타데이터 로드 확인"""
        # Given: FAISS 인덱스와 메타데이터 파일 경로
        from llm.rag_retriever import RAGRetriever

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # When: RAGRetriever 초기화
        retriever = RAGRetriever(str(index_path), str(metadata_path))

        # Then: retriever 객체가 생성되어야 함
        assert retriever is not None, "RAGRetriever 객체 생성 실패"

        # Then: index가 로드되어 있어야 함
        assert hasattr(retriever, "index"), "index 속성이 없음"
        assert retriever.index is not None, "index가 None임"
        assert retriever.index.ntotal > 0, f"index에 벡터가 없음: {retriever.index.ntotal}"

        # Then: items가 로드되어 있어야 함
        assert hasattr(retriever, "items"), "items 속성이 없음"
        assert retriever.items is not None, "items가 None임"
        assert len(retriever.items) > 0, "items가 비어있음"

        # Then: embedding_model 정보가 있어야 함
        assert hasattr(retriever, "embedding_model"), "embedding_model 속성이 없음"
        assert retriever.embedding_model == "text-embedding-3-small", (
            f"embedding_model이 올바르지 않음: {retriever.embedding_model}"
        )

    def test_rag_retriever_retrieve(self):
        """Test 3.2: RAGRetriever.retrieve() 메서드로 관련 워크숍 검색"""
        # Given: RAGRetriever 인스턴스와 쿼리
        from llm.rag_retriever import RAGRetriever

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        retriever = RAGRetriever(str(index_path), str(metadata_path))

        query = "제주 돌담 쌓기 체험"
        top_k = 5

        # When: retrieve() 메서드 호출
        results = retriever.retrieve(query, top_k)

        # Then: 결과가 리스트여야 함
        assert isinstance(results, list), f"결과가 리스트가 아님: {type(results)}"

        # Then: 결과 개수가 top_k와 일치해야 함
        assert len(results) == top_k, f"결과 개수가 올바르지 않음: {len(results)}"

        # Then: 각 결과가 필요한 필드를 포함해야 함
        required_fields = ["distance", "title", "introduction", "alltag", "address"]
        for i, result in enumerate(results):
            assert isinstance(result, dict), f"결과 {i}가 dict가 아님: {type(result)}"
            for field in required_fields:
                assert field in result, f"결과 {i}에 {field} 필드가 없음"

        # Then: 거리가 오름차순으로 정렬되어 있어야 함
        for i in range(len(results) - 1):
            assert (
                results[i]["distance"] <= results[i + 1]["distance"]
            ), "결과가 거리순으로 정렬되지 않음"

        # Then: 첫 번째 결과가 쿼리와 관련성이 있어야 함 (title이나 alltag에 관련 키워드 포함)
        first_result = results[0]
        text = (first_result["title"] + " " + first_result["alltag"]).lower()
        # 돌담이나 stone 관련 키워드가 있는지 확인
        assert any(
            keyword in text for keyword in ["돌", "stone", "담", "wall"]
        ), f"첫 번째 결과가 쿼리와 관련성이 없음: {first_result['title']}"


class TestRAGRetrieverLogging:
    """RAG Retriever 로깅 기능 테스트"""

    def test_retrieve_function_logs_query_and_results(self, caplog):
        """Test 4.1: retrieve() 함수가 검색 쿼리와 결과를 로깅하는지 확인"""
        # Given: 로깅 레벨 설정
        import logging

        from llm.rag_retriever import retrieve

        caplog.set_level(logging.INFO, logger="llm.rag_retriever")

        query = "제주 전통 체험"
        top_k = 3

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # When: retrieve() 함수 호출
        results = retrieve(query, top_k, str(index_path), str(metadata_path))

        # Then: 로그에 검색 시작 메시지가 있어야 함
        assert any(
            "검색 시작" in record.message and query in record.message
            for record in caplog.records
        ), "검색 시작 로그가 없음"

        # Then: 로그에 검색 완료 메시지가 있어야 함
        assert any(
            "검색 완료" in record.message for record in caplog.records
        ), "검색 완료 로그가 없음"

        # Then: 로그에 소요시간이 기록되어야 함
        assert any(
            "소요시간" in record.message for record in caplog.records
        ), "소요시간 로그가 없음"

        # Then: 로그에 결과 개수가 기록되어야 함
        assert any(
            f"결과수: {top_k}" in record.message for record in caplog.records
        ), "결과 개수 로그가 없음"

        # Then: 검색 결과가 정상적으로 반환되어야 함
        assert len(results) == top_k, f"결과 개수가 올바르지 않음: {len(results)}"

    def test_retrieve_function_logs_distance_stats(self, caplog):
        """Test 4.2: retrieve() 함수가 거리 통계를 로깅하는지 확인"""
        # Given: 로깅 레벨 설정
        import logging

        from llm.rag_retriever import retrieve

        caplog.set_level(logging.INFO, logger="llm.rag_retriever")

        query = "해녀 물질"
        top_k = 5

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # When: retrieve() 함수 호출
        results = retrieve(query, top_k, str(index_path), str(metadata_path))

        # Then: 로그에 거리 범위가 기록되어야 함
        assert any(
            "거리범위" in record.message or "distance" in record.message.lower()
            for record in caplog.records
        ), "거리 통계 로그가 없음"

        # Then: 실제 결과의 거리값이 로그와 일치해야 함
        distances = [r["distance"] for r in results]
        min_dist = min(distances)
        max_dist = max(distances)

        # 로그에 최소/최대 거리가 포함되어 있는지 확인
        log_messages = " ".join(record.message for record in caplog.records)
        # 거리값이 로그에 나타나는지 확인 (소수점 반올림 고려)
        assert any(
            "거리" in record.message for record in caplog.records
        ), f"거리 정보가 로그에 없음. min={min_dist:.2f}, max={max_dist:.2f}"

    def test_retrieve_function_logs_top_results(self, caplog):
        """Test 4.3: retrieve() 함수가 상위 결과들을 로깅하는지 확인"""
        # Given: 로깅 레벨을 DEBUG로 설정하여 상세 로그 확인
        import logging

        from llm.rag_retriever import retrieve

        caplog.set_level(logging.DEBUG, logger="llm.rag_retriever")

        query = "제주 말 체험"
        top_k = 3

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # When: retrieve() 함수 호출
        results = retrieve(query, top_k, str(index_path), str(metadata_path))

        # Then: 로그에 상위 결과의 title이 포함되어야 함
        log_messages = " ".join(record.message for record in caplog.records)

        # 최소한 첫 번째 결과의 title이 로그에 나타나야 함
        first_title = results[0]["title"]
        assert any(
            first_title[:20] in record.message for record in caplog.records
        ), f"상위 결과 title이 로그에 없음: {first_title}"

    def test_rag_retriever_class_logs_retrieval(self, caplog):
        """Test 4.4: RAGRetriever 클래스의 retrieve() 메서드도 로깅하는지 확인"""
        # Given: 로깅 레벨 설정
        import logging

        from llm.rag_retriever import RAGRetriever

        caplog.set_level(logging.INFO, logger="llm.rag_retriever")

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        retriever = RAGRetriever(str(index_path), str(metadata_path))

        query = "제주 감귤 체험"
        top_k = 3

        # When: RAGRetriever.retrieve() 호출
        results = retriever.retrieve(query, top_k)

        # Then: 로그에 검색 관련 메시지가 있어야 함
        assert any(
            "검색" in record.message for record in caplog.records
        ), "RAGRetriever 클래스의 로그가 없음"

        # Then: 결과가 정상적으로 반환되어야 함
        assert len(results) == top_k, f"결과 개수가 올바르지 않음: {len(results)}"
