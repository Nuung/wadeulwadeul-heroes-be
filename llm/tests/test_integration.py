"""통합 테스트 및 최적화 테스트"""

import os
import sys
import time
from pathlib import Path

import pytest

if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY is required for RAG integration tests", allow_module_level=True)

# llm 모듈을 임포트하기 위한 경로 설정
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestIntegration:
    """통합 테스트"""

    def test_e2e_experience_plan(self):
        """Test 5.1: 실제 카테고리로 RAG + 프롬프트 전체 흐름 테스트"""
        # Given: example_rag_usage의 함수들
        from llm.example_rag_usage import (
            build_rag_context,
            enhanced_experience_plan_prompt,
        )

        # 다양한 카테고리 테스트
        categories = ["해녀", "요리", "목공", "돌담"]

        for category in categories:
            # When: RAG 컨텍스트 생성
            rag_context = build_rag_context(category, top_k=3)

            # Then: RAG 컨텍스트가 생성되어야 함
            assert rag_context, f"{category} 카테고리의 RAG 컨텍스트가 비어있음"
            assert "<similar_workshops>" in rag_context, "시작 태그가 없음"
            assert "</similar_workshops>" in rag_context, "종료 태그가 없음"
            assert "[워크숍 1]" in rag_context, "워크숍 정보가 없음"

        # When: 전체 프롬프트 생성 (해녀 체험)
        prompt = enhanced_experience_plan_prompt(
            category="해녀",
            years_of_experience="15",
            job_description="제주 해녀",
            materials="테왁, 망사리, 잠수복",
            location="제주시 조천읍",
            duration_minutes="90",
            capacity="6",
            price_per_person="80000",
        )

        # Then: 프롬프트에 필수 요소가 포함되어야 함
        assert "<class_information>" in prompt, "class_information이 없음"
        assert "<similar_workshops>" in prompt, "similar_workshops가 없음"
        assert "해녀" in prompt, "카테고리가 포함되지 않음"
        assert "테왁" in prompt, "재료가 포함되지 않음"

    def test_retrieval_performance(self):
        """Test 5.2: 검색 속도가 합리적인지 확인 (< 500ms)"""
        # Given: RAGRetriever 인스턴스
        from llm.rag_retriever import RAGRetriever

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        retriever = RAGRetriever(str(index_path), str(metadata_path))

        # When: 검색 수행 및 시간 측정
        query = "제주 전통 요리 체험"
        start_time = time.time()
        results = retriever.retrieve(query, top_k=5)
        elapsed_time = (time.time() - start_time) * 1000  # ms

        # Then: 검색이 성공해야 함
        assert len(results) == 5, f"결과 개수가 올바르지 않음: {len(results)}"

        # Then: 검색 시간이 500ms 이하여야 함
        assert (
            elapsed_time < 500
        ), f"검색 시간이 너무 김: {elapsed_time:.2f}ms (목표: < 500ms)"

        print(f"\n✓ 검색 성능: {elapsed_time:.2f}ms (목표: < 500ms)")

        # 여러 번 검색하여 평균 성능 확인
        times = []
        for _ in range(5):
            start = time.time()
            retriever.retrieve(query, top_k=3)
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)
        assert avg_time < 500, f"평균 검색 시간이 너무 김: {avg_time:.2f}ms"

        print(f"✓ 평균 검색 성능 (5회): {avg_time:.2f}ms")

    def test_error_handling(self):
        """Test 5.3: 인덱스 파일 없음, API 오류 등 예외 상황 처리"""
        # Test 5.3a: 존재하지 않는 인덱스 파일
        from llm.rag_retriever import RAGRetriever

        with pytest.raises((RuntimeError, FileNotFoundError)):
            RAGRetriever("nonexistent_index.index", "nonexistent_metadata.json")

        # Test 5.3b: retrieve 함수 - 존재하지 않는 파일
        from llm.rag_retriever import retrieve

        with pytest.raises((RuntimeError, FileNotFoundError)):
            retrieve("테스트 쿼리", index_path="nonexistent.index")

        # Test 5.3c: 빈 쿼리 처리
        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        retriever = RAGRetriever(str(index_path), str(metadata_path))

        # 빈 쿼리도 처리되어야 함 (오류 없이)
        results = retriever.retrieve("", top_k=1)
        assert isinstance(results, list), "빈 쿼리도 리스트를 반환해야 함"

        print("\n✓ 오류 처리 테스트 통과")


class TestOptimization:
    """최적화 관련 테스트"""

    def test_batch_retrieval(self):
        """여러 쿼리를 배치로 처리하는 성능 테스트"""
        # Given: RAGRetriever와 여러 쿼리
        from llm.rag_retriever import RAGRetriever

        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        retriever = RAGRetriever(str(index_path), str(metadata_path))

        queries = [
            "제주 해녀 체험",
            "제주 돌담 쌓기",
            "제주 전통 요리",
            "제주 감귤 수확",
            "제주 목공 체험",
        ]

        # When: 배치 검색 수행
        start_time = time.time()
        results_list = [retriever.retrieve(q, top_k=3) for q in queries]
        elapsed_time = (time.time() - start_time) * 1000

        # Then: 모든 쿼리가 처리되어야 함
        assert len(results_list) == len(queries), "배치 처리 실패"

        for i, results in enumerate(results_list):
            assert len(results) == 3, f"쿼리 {i}의 결과 개수가 올바르지 않음"

        # Then: 배치 처리 시간이 합리적이어야 함 (쿼리당 평균 < 500ms)
        avg_per_query = elapsed_time / len(queries)
        assert (
            avg_per_query < 500
        ), f"쿼리당 평균 시간이 너무 김: {avg_per_query:.2f}ms"

        print(f"\n✓ 배치 처리 성능: {len(queries)}개 쿼리, {elapsed_time:.2f}ms")
        print(f"  쿼리당 평균: {avg_per_query:.2f}ms")
