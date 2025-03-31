import json
import mimetypes
import socket
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 3000

UDP_HOST = "127.0.0.1"
UDP_PORT = 5000


class HttpHandler(BaseHTTPRequestHandler):
    """Обробник HTTP-запитів."""
    def do_POST(self):
        """Обробка POST-запиту з форми. Дані пересилаються на UDP-сервер."""
        data = self.rfile.read(int(self.headers['Content-Length']))

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            server_address = (UDP_HOST, UDP_PORT)
            sock.sendto(data, server_address)
            response = sock.recv(1024)

        if response.decode() == "200 OK":
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

    def do_GET(self):
        """Обробка GET-запиту. Повертає HTML-сторінку або статичний ресурс, або сторінку 404."""
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('templates/index.html')
        elif pr_url.path == '/message':
            self.send_html_file('templates/message.html')
        else:
            if Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('templates/error.html', 404)

    def send_html_file(self, filename, status=200):
        """Надсилає HTML-файл у відповідь клієнту."""
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        """Надсилає статичний файл (CSS, зображення тощо) клієнту. Тип контенту визначається автоматично."""
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def store_message(data: dict[str, Any], filename: str = "data.json"):
    """Додає повідомлення у JSON-файл зі збереженням часу отримання."""
    storage_path = Path("storage") / filename
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    messages = {}
    if storage_path.exists():
        try:
            with storage_path.open("r", encoding="utf-8") as f:
                messages = json.load(f)
        except json.JSONDecodeError:
            pass

    messages[str(datetime.now(timezone.utc))] = data

    with open(storage_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def run_client():
    """Запускає HTTP-сервер для обслуговування веб-запитів."""
    server_address = (HTTP_HOST, HTTP_PORT)
    
    with HTTPServer(server_address, HttpHandler) as httpd:
        httpd.serve_forever()


def run_server():
    """Запускає UDP-сервер, який приймає дані з форми, обробляє та зберігає у файл."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        server_address = (UDP_HOST, UDP_PORT)
        sock.bind(server_address)

        while True:
            data, address = sock.recvfrom(1024)

            data_parse = urllib.parse.unquote_plus(data.decode())
            data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
            store_message(data_dict)
            
            sock.sendto(b"200 OK", address)


if __name__ == '__main__':
    """Точка входу програми. Запускає HTTP та UDP сервери в окремих потоках."""
    http_thread = threading.Thread(target=run_client, daemon=True)
    udp_thread = threading.Thread(target=run_server, daemon=True)

    http_thread.start()
    udp_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
