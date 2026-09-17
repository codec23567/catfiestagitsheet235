"""
워크플로우별로 "어떤 셀을 읽고 어떤 셀에 쓸지"만 정의하는 설정 파일.

새 워크플로우를 추가하고 싶으면:
  1) 아래 WORKFLOW_CELLS 에 항목 하나 추가
  2) webhook.py 의 WORKFLOWS 딕셔너리에 항목 하나 추가
그게 끝입니다. 새 폴더/새 파일을 만들 필요가 없습니다.

각 항목 의미:
  url_cell    : 수정할 게시글 URL이 들어있는 셀
  html_cell   : 수정할 본문 HTML이 들어있는 셀
  status_cell : 실행 상태("실행중"/"완료"/"실패 : ...")를 기록할 셀
  done_cell   : 완료 시각을 기록할 셀

[이름 변경] m_html / m_normal -> m_html_one / m_html_two
둘 다 HTML 모드로 게시글을 수정하는 동일한 로직이라(대상 셀만 다름),
"normal"이라는 이름이 오히려 혼동을 줘서 m_html_one(시리즈관리, I3),
m_html_two(특수 게시글, I11)로 이름을 통일했습니다.
"""

WORKFLOW_CELLS = {
    "m_html_one": {
        "url_cell": "C3",
        "html_cell": "I5",
        "status_cell": "I7",
        "done_cell": "I8",
    },
    "m_html_two": {
        "url_cell": "I12",
        "html_cell": "I13",
        "status_cell": "I15",
        "done_cell": "I16",
    },
    # 새 워크플로우 추가 예시:
    # "m_html_three": {
    #     "url_cell": "K3",
    #     "html_cell": "K5",
    #     "status_cell": "K7",
    #     "done_cell": "K8",
    # },
}
