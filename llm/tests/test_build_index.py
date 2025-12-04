"""FAISS 인덱스 생성 및 로드 테스트"""

import json
import os
import subprocess
from pathlib import Path

import faiss
import pytest

if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY is required for build_index tests", allow_module_level=True)


class TestBuildIndex:
    """FAISS 인덱스 빌드 테스트"""

    def test_build_faiss_index(self):
        """Test 1.1: build_index.py 실행 후 index 파일과 metadata 파일이 생성되는지 확인"""
        # Given: 프로젝트 루트와 출력 경로
        project_root = Path(__file__).parent.parent.parent
        build_script = project_root / "llm" / "build_index.py"
        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # 기존 파일 삭제 (테스트 격리)
        if index_path.exists():
            index_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

        # When: build_index.py 실행
        result = subprocess.run(
            ["uv", "run", "python", str(build_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
        )

        # Then: 스크립트가 성공적으로 실행되어야 함
        assert result.returncode == 0, f"build_index.py 실행 실패:\n{result.stderr}"

        # Then: index 파일이 생성되어야 함
        assert index_path.exists(), f"FAISS index 파일이 생성되지 않음: {index_path}"

        # Then: metadata 파일이 생성되어야 함
        assert (
            metadata_path.exists()
        ), f"metadata 파일이 생성되지 않음: {metadata_path}"

        # Then: 파일들이 비어있지 않아야 함
        assert index_path.stat().st_size > 0, "FAISS index 파일이 비어있음"
        assert metadata_path.stat().st_size > 0, "metadata 파일이 비어있음"

    def test_load_faiss_index(self):
        """Test 1.2: 생성된 FAISS 인덱스를 정상적으로 로드할 수 있는지 확인"""
        # Given: FAISS 인덱스 파일 경로
        project_root = Path(__file__).parent.parent.parent
        index_path = project_root / "llm" / "output" / "visitjeju_faiss.index"

        # 인덱스 파일이 존재하는지 확인
        assert index_path.exists(), f"FAISS index 파일이 없음: {index_path}"

        # When: FAISS 인덱스 로드
        index = faiss.read_index(str(index_path))

        # Then: 인덱스가 정상적으로 로드되어야 함
        assert index is not None, "FAISS 인덱스 로드 실패"

        # Then: 인덱스가 학습되어 있어야 함
        assert index.is_trained, "FAISS 인덱스가 학습되지 않음"

        # Then: 인덱스에 벡터가 존재해야 함
        assert index.ntotal > 0, f"FAISS 인덱스에 벡터가 없음. ntotal={index.ntotal}"

        # Then: 벡터 차원이 올바른지 확인 (text-embedding-3-small: 1536)
        assert index.d == 1536, f"벡터 차원이 올바르지 않음. expected=1536, actual={index.d}"

    def test_load_metadata(self):
        """Test 1.3: metadata.json을 로드하고 items와 embedding_model 정보를 확인"""
        # Given: 메타데이터 파일 경로
        project_root = Path(__file__).parent.parent.parent
        metadata_path = project_root / "llm" / "output" / "visitjeju_metadata.json"

        # 메타데이터 파일이 존재하는지 확인
        assert metadata_path.exists(), f"metadata 파일이 없음: {metadata_path}"

        # When: 메타데이터 로드
        with metadata_path.open(encoding="utf-8") as f:
            metadata = json.load(f)

        # Then: 메타데이터가 올바른 구조여야 함
        assert "embedding_model" in metadata, "embedding_model 키가 없음"
        assert "items" in metadata, "items 키가 없음"

        # Then: embedding_model이 올바른지 확인
        assert (
            metadata["embedding_model"] == "text-embedding-3-small"
        ), f"embedding_model이 올바르지 않음: {metadata['embedding_model']}"

        # Then: items가 리스트이고 비어있지 않아야 함
        assert isinstance(metadata["items"], list), "items가 리스트가 아님"
        assert len(metadata["items"]) > 0, "items가 비어있음"

        # Then: 첫 번째 item이 올바른 구조를 가지는지 확인
        first_item = metadata["items"][0]
        assert "title" in first_item, "item에 title 키가 없음"
