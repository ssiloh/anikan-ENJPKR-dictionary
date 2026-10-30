"""out/site 를 로컬 서버로 띄운다: python -m anikan.serve [--port 8000] [--host 0.0.0.0]
폰에서는 Tailscale 주소(http://<tailscale-ip>:8000)로 접속한다. 데이터는 공개 라이선스지만 포트를 인터넷에 직접 열지는 말 것."""
import argparse
import functools
import http.server

from anikan.common import OUT


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith((".json", ".js", ".css", ".html", ".md")):
            self.send_header("Cache-Control", "no-cache")      # 개발 중 갱신이 바로 보이게(JSON 샤드는 브라우저가 앱 안에서 따로 캐시)
        super().end_headers()

    def guess_type(self, path):
        return "text/markdown; charset=utf-8" if str(path).endswith(".md") else super().guess_type(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT / "site"))
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    handler = functools.partial(Handler, directory=a.dir)
    with http.server.ThreadingHTTPServer((a.host, a.port), handler) as srv:
        print(f"http://{'localhost' if a.host == '0.0.0.0' else a.host}:{a.port}  ({a.dir})  Ctrl+C 로 종료")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
