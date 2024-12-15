import socket
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process
from pymongo import MongoClient
import mimetypes
import pathlib
import urllib.parse

STATIC_DIR = "front-init"


# HTTP Server class
class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file(f"{STATIC_DIR}/index.html")
        elif pr_url.path == "/message.html":
            self.send_html_file(f"{STATIC_DIR}/message.html")
        else:
            static_path = pathlib.Path().joinpath(STATIC_DIR, pr_url.path[1:])
            if static_path.exists():
                self.send_static(static_path)
            else:
                self.send_html_file(f"{STATIC_DIR}/error.html", 404)

    def do_POST(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/message":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            form_data = urllib.parse.parse_qs(post_data)

            username = form_data.get("username", [""])[0]
            message = form_data.get("message", [""])[0]

            if username and message:
                self.send_to_socket_server(username, message)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Message sent successfully!")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid data received.")
        else:
            self.send_response(404)
            self.end_headers()

    def send_html_file(self, file_name, content_type="text/html"):
        try:
            with open(file_name, "rb") as file:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_error(404, "Page not found")
            self.send_html_file("error.html")

    def send_static(self, static_path):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(static_path, "rb") as file:
            self.wfile.write(file.read())

    def send_to_socket_server(self, username, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5000))
                data = f"{username}|{message}"
                sock.sendall(data.encode("utf-8"))
        except Exception as e:
            print(f"Error sending data to socket server: {e}")


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ("", 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


# Socket Server
def run_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("", 5000))
    server.listen(5)

    client = MongoClient('mongodb://root:example@mongo:27017/messages_db?authSource=admin')
    db = client.messages_db
    collection = db.messages

    while True:
        conn, addr = server.accept()
        data = conn.recv(1024)
        if data:
            decoded_data = data.decode("utf-8")
            username, message = decoded_data.split("|")
            entry = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": username,
                "message": message,
            }

            collection.insert_one(entry)
            print("Message saved:", entry)
        conn.close()


if __name__ == "__main__":
    p1 = Process(target=run_http_server)
    p2 = Process(target=run_socket_server)

    p1.start()
    p2.start()
