import requests
import sys


def dump_html(url, output_path="dump.html"):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=30)

    print(f"[응답] 상태={response.status_code}, 바이트={len(response.content)}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"[저장 완료] {output_path}")


if __name__ == "__main__":

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("URL 입력: ").strip()

    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        output_path = "dump.html"

    dump_html(url, output_path)
