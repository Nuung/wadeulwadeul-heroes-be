import os

# 테스트 실행 시에는 로컬 설정을 강제하여 SQLite 사용 및 스키마 오류를 방지한다.
os.environ.setdefault("ENVIRONMENT", "local")
