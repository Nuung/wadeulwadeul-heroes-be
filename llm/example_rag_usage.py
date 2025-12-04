"""RAG 사용 예제

experience_plan 프롬프트에 RAG 컨텍스트를 추가하여 사용하는 예제입니다.
"""

from pathlib import Path

from rag_retriever import RAGRetriever

# RAGRetriever 초기화
BASE_DIR = Path(__file__).parent
index_path = BASE_DIR / "output" / "visitjeju_faiss.index"
metadata_path = BASE_DIR / "output" / "visitjeju_metadata.json"

retriever = RAGRetriever(str(index_path), str(metadata_path))


def build_rag_context(category: str, top_k: int = 3) -> str:
    """카테고리에 맞는 RAG 컨텍스트 생성

    Args:
        category: 체험 유형 (예: "해녀", "요리", "목공")
        top_k: 검색할 워크숍 개수

    Returns:
        프롬프트에 추가할 RAG 컨텍스트 문자열
    """
    # 카테고리로 유사 워크숍 검색
    query = f"제주 {category} 체험 프로그램"
    results = retriever.retrieve(query, top_k)

    # RAG 컨텍스트 구성
    context_lines = ["<similar_workshops>", "참고: 제주의 유사한 체험 프로그램들입니다.", ""]

    for i, result in enumerate(results, 1):
        context_lines.append(f"[워크숍 {i}]")
        context_lines.append(f"제목: {result['title']}")
        context_lines.append(f"소개: {result['introduction']}")
        context_lines.append(f"태그: {result['alltag']}")
        context_lines.append(f"주소: {result['address']}")
        context_lines.append("")

    context_lines.append("</similar_workshops>")

    return "\n".join(context_lines)


def enhanced_experience_plan_prompt(
    category: str,
    years_of_experience: str,
    job_description: str,
    materials: str,
    location: str,
    duration_minutes: str,
    capacity: str,
    price_per_person: str,
) -> str:
    """RAG 컨텍스트가 추가된 experience plan 프롬프트

    Args:
        category: 체험 유형
        years_of_experience: 해당 분야 경력 (년수)
        job_description: 직업/전문 분야
        materials: 준비 재료
        location: 만나는 장소
        duration_minutes: 소요 시간 (분)
        capacity: 최대 참여 인원
        price_per_person: 1인당 요금

    Returns:
        RAG 컨텍스트가 포함된 user prompt
    """
    # RAG 컨텍스트 생성
    rag_context = build_rag_context(category, top_k=3)

    # 기존 프롬프트에 RAG 컨텍스트 추가
    prompt = f"""
다음 정보를 바탕으로 체험 클래스의 전체 템플릿을 작성해 주세요:

<class_information>
- 체험 유형: {category}
- 호스트 경력: {years_of_experience}년
- 호스트 직업/전문 분야: {job_description}
- 준비 재료: {materials}
- 만나는 장소: {location}
- 총 소요 시간: {duration_minutes}분
- 최대 참여 인원: {capacity}명
- 1인당 요금: {price_per_person}원
</class_information>

{rag_context}

위 정보를 활용하여 호스트가 실제 체험을 진행할 때 사용할 수 있는 상세한 템플릿을 작성해 주세요.
유사한 워크숍 정보를 참고하여, 제주 지역의 특색을 살린 체험 프로그램으로 구성해 주세요.
시간 배분은 총 {duration_minutes}분에 맞춰 오프닝, 준비, 핵심 체험, 마무리로 구성해 주세요.
반드시 JSON만 출력해 주세요.
"""

    return prompt.strip()


if __name__ == "__main__":
    # 사용 예제
    print("=" * 80)
    print("RAG를 활용한 Experience Plan 프롬프트 생성 예제")
    print("=" * 80)

    # 예제 데이터
    prompt = enhanced_experience_plan_prompt(
        category="해녀",
        years_of_experience="15",
        job_description="제주 해녀",
        materials="테왁, 망사리, 잠수복, 오리발",
        location="제주시 조천읍 바닷가",
        duration_minutes="90",
        capacity="6",
        price_per_person="80000",
    )

    print(prompt)
    print("\n" + "=" * 80)
