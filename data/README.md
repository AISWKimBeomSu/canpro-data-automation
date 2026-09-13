# data/

이 폴더의 실제 데이터는 **개인정보 보호를 위해 저장소에 포함하지 않습니다.**
(참가자 식이 원물, 매핑 결과, 사용자 정보, 로그, CAN-Pro 식품 DB 등은 모두 `.gitignore` 처리)

로컬에서 실행하려면 아래 파일을 직접 채워야 합니다.

| 파일 | 설명 |
|---|---|
| `Food_Database_Complete.xlsx` | CAN-Pro 공개 식품 DB (음식_전체_DB 시트: 식품명·식품 번호) |
| `input_raw.tsv` | 참가자 원물 데이터 (ID·성명·조회일·구분·시간대·음식명) |
| `mapped_rows.tsv` | 전처리 산출물 (build_mapping.py 실행 결과, 자동 생성) |
| `user_info.tsv` | 사용자 기본정보 (register_users.py 입력용) |

> 개인정보는 가명 ID·마스킹 등 비식별 처리 후에만 다룹니다.
