import os
import json
import subprocess
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env 파일에서 CAT_ID, CAT_PW 읽기.
def load_env_file(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

CAT_ENV = load_env_file(os.path.join(BASE_DIR, ".env"))

with open(os.path.join(BASE_DIR, "credentials.json")) as f:
    GOOGLE_CREDENTIALS = f.read()

# 인증용 비밀 토큰 (아무나 이 서버를 호출 못하게 막는 용도)
WEBHOOK_SECRET = CAT_ENV.get("WEBHOOK_SECRET", "changeme")

# 워크플로우 이름 -> (실행 폴더, 실행할 스크립트(리스트로, 인자 포함 가능), CAT 로그인 필요 여부)
#
# [변경] m_html_one / m_html_two 는 이제 각자 폴더(modify_html_ver / modify_normal_ver)를
# 쓰지 않고, modify_html_unity_ver/read_host_html_unity.py 를 워크플로우 이름을 인자로
# 넘겨서 공용으로 실행합니다. (modify_html_unity_ver/workflow_config.py 에 셀 주소가 정의되어 있음)
# 새 워크플로우가 "로직은 같고 셀 주소만 다른" 경우라면, 새 폴더를 만들 필요 없이
# modify_html_unity_ver/workflow_config.py 에 항목을 추가하고 여기에 한 줄만 추가하면 됩니다.
#
# [이름 변경] m_html / m_normal -> m_html_one / m_html_two
# 둘 다 HTML 모드로 게시글을 수정하는 동일한 로직이라(대상 셀만 다름),
# "normal"이라는 이름이 오히려 혼동을 줘서 m_html_one(시리즈관리, I3),
# m_html_two(특수 게시글, I11)로 이름을 통일했습니다.
#
# "workflow"는 두 가지 의미 중 하나로 쓰입니다.
#  - 여기서는 내부 작업 이름표(m_html_one, m_html_two 등)라는 의미로 쓰임
#  - GitHub Actions 워크플로우(.yml 파일)는 다른 의미

WORKFLOWS = {
    "nickdate": ("nickdate", ["select_organize_nickdate.py"], False),
    "image": ("image", ["select_organize_image.py"], False),
    "m_html_one": ("modify_html_unity_ver", ["read_host_html_unity.py", "m_html_one"], True),
    "m_html_two": ("modify_html_unity_ver", ["read_host_html_unity.py", "m_html_two"], True),
    "m_normal_bl": ("modify_normal_bl_ver", ["read_host_normal_bl.py"], True),
}

# ------------------------------------------------------------------
# 같은 시트 + 같은 워크플로우가 동시에 두 번 실행되는 것을 막는 잠금 장치
# key: (workflow, sheet_name), value: True(작업중)
# "같은 시트 + 같은 워크플로우" 중복만 막고
# "같은 시트 + 다른 워크플로우"는 병렬 실행을 허용한다.
# ------------------------------------------------------------------
running_lock = threading.Lock()
running_jobs = set()

# 스크립트가 아무리 길어도 이 시간(초)이 지나면 강제로 실패 처리
SCRIPT_TIMEOUT_SECONDS = 120


def run_script(folder, script_args, needs_cat_login, sheet_name):
    """
    스크립트를 실행하고 '실제로 끝날 때까지' 기다린 뒤
    (성공여부, 로그일부) 를 돌려주는 함수.

    script_args: 예) ["read_host_html_unity.py", "m_html_one"]
                 (기존에는 ["read_host_html.py"] 처럼 파일 하나였지만,
                  이제 워크플로우 이름을 인자로 추가로 넘길 수 있도록
                  리스트를 그대로 받습니다.)
    """
    env = os.environ.copy()
    env["GOOGLE_CREDENTIALS"] = GOOGLE_CREDENTIALS
    env["TARGET_SHEET"] = sheet_name
    if needs_cat_login:
        env["CAT_ID"] = CAT_ENV.get("CAT_ID", "")
        env["CAT_PW"] = CAT_ENV.get("CAT_PW", "")

    script_dir = os.path.join(BASE_DIR, folder)
    log_path = os.path.join(BASE_DIR, "logs", f"{folder}.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as logf:
        logf.write(f"\n\n===== 실행: {' '.join(script_args)} / 시트: {sheet_name} =====\n")
        logf.flush()

        try:
            # timeout 추가: 너무 오래 걸리면 강제 종료
            result = subprocess.run(
                ["/root/myproject/venv/bin/python3", *script_args],
                cwd=script_dir,
                env=env,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=SCRIPT_TIMEOUT_SECONDS
            )
            success = (result.returncode == 0)
            if not success:
                logf.write(f"\n[webhook] 스크립트 종료코드 비정상: {result.returncode}\n")
            return success, None

        except subprocess.TimeoutExpired:
            logf.write(f"\n[webhook] 시간초과({SCRIPT_TIMEOUT_SECONDS}초) - 강제 종료\n")
            return False, f"시간초과 {SCRIPT_TIMEOUT_SECONDS}초 초과"

        except Exception as e:
            logf.write(f"\n[webhook] 예외 발생: {e}\n")
            return False, str(e)


@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(silent=True)  # force=True -> silent=True (이상한 요청에도 500 안 나게)

    if not data:
        return jsonify({"error": "invalid json body"}), 400

    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    workflow = data.get("workflow")
    sheet_name = data.get("sheet_name")

    if workflow not in WORKFLOWS:
        return jsonify({"error": f"unknown workflow: {workflow}"}), 400
    if not sheet_name:
        return jsonify({"error": "sheet_name required"}), 400

    # job_key = (workflow, sheet_name)
    # 같은 시트라도 워크플로우가 다르면 서로 다른 job으로 취급해서
    # 병렬 실행을 허용한다. 완전히 동일한 (workflow, sheet_name) 조합만
    # 중복 실행을 막는다.
    job_key = (workflow, sheet_name)

    with running_lock:
        if job_key in running_jobs:
            return jsonify({
                "success": False,
                "error": f"'{sheet_name}' 시트의 '{workflow}' 작업이 이미 진행중입니다. 잠시 후 다시 시도하세요."
            }), 409  # 409 = Conflict(충돌)
        running_jobs.add(job_key)

    folder, script_args, needs_cat_login = WORKFLOWS[workflow]

    try:
        # 백그라운드로 던지고 바로 끝내는 게 아니라
        # 여기서 실제로 끝날 때까지 기다림
        success, error_detail = run_script(folder, script_args, needs_cat_login, sheet_name)
    finally:
        # 작업 끝났으니 잠금 해제 (성공하든 실패하든 반드시 실행)
        with running_lock:
            running_jobs.discard(job_key)

    if success:
        return jsonify({
            "success": True,
            "status": "completed",
            "workflow": workflow,
            "sheet_name": sheet_name
        }), 200
    else:
        # 실패했으면 200이 아니라 500을 반환
        # -> Apps Script가 이걸 보고 진짜 실패임을 알고 깃허브 백업으로 넘어갈 수 있음
        return jsonify({
            "success": False,
            "status": "failed",
            "workflow": workflow,
            "sheet_name": sheet_name,
            "error": error_detail
        }), 500


if __name__ == "__main__":
    # threaded=True:
    # 기존에는 Flask 개발 서버가 기본적으로 싱글 스레드라, 서로 다른
    # 워크플로우 요청이라도 앞 요청이 끝날 때까지 뒤 요청이 대기해야 했다.
    # threaded=True로 바꾸면 요청마다 별도 스레드에서 처리되어
    # nickdate/image처럼 서로 다른 워크플로우를 진짜로 동시에 실행할 수 있다.
    app.run(host="0.0.0.0", port=5000, threaded=True)
