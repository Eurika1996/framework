#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock CSGClaw Server - 模拟 CSGClaw UI 服务
"""

import http.server
import socketserver
import os
import sys
import json
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MockHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == '/healthz':
                self._send_json({"status": "ok", "service": "mock-csgclaw"})
                return

            if path.startswith('/api/'):
                self._send_json({"status": "ok", "path": path})
                return

            html_path = os.path.join(BASE_DIR, 'index.html')
            with open(html_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except BrokenPipeError:
            pass
        except Exception:
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Server Error")
            except:
                pass

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            if length > 0:
                self.rfile.read(length)
            self._send_json({"status": "ok", "path": urlparse(self.path).path})
        except Exception:
            pass

    def _send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(port=18080):
    os.chdir(BASE_DIR)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", port), MockHandler)
    server.allow_reuse_address = True

    print(f"\n{'='*50}")
    print(f"  Mock CSGClaw Server - 端口 {port}")
    print(f"  访问: http://127.0.0.1:{port}/")
    print(f"{'='*50}\n")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("服务已停止")
        server.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18080
    start_server(port)
