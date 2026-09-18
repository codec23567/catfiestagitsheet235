# 워크플로우별로 "어떤 셀을 읽고 어떤 셀에 쓸지"만 정의하는 설정 파일.
# 새 워크플로우를 추가 시 :
#   1) 아래 WORKFLOW_CELLS 에 항목 하나 추가
#   2) webhook.py 의 WORKFLOWS 딕셔너리에 항목 하나 추가

#   url_cell    : 수정할 게시글 URL 셀
#   html_cell   : 수정할 본문 HTML 셀
#   status_cell : 실행 상태("실행중"/"완료"/"실패 : ...")를 기록할 셀
#   done_cell   : 완료 시각을 기록할 셀


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


}
