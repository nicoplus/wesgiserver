import socket
from io import BytesIO
import sys
from datetime import datetime


class WSGIServer:

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, server_address):
        self.listen_socket = listen_socket = socket.socket(
            self.address_family, self.socket_type)

        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(server_address)
        listen_socket.listen(self.request_queue_size)

        host, port = self.listen_socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

        self.header_set = []

    def get_app(self, application):
        self.application = application

    def server_forver(self):
        listen_socket = self.listen_socket
        while True:
            self.client_connect, self.client_address = listen_socket.accept()
            self.handle_one_request()

    def handle_one_request(self):
        self.request_data = request_data = self.client_connect.recv(1024)

        print(''.join('<{line}\n'.format(line=line)
                      for line in request_data.splitlines()
                      ))

        self.parse_request(request_data)

        env = self.get_environ()

        result = self.application(env, self.start_response)

        self.finish_response(result)

    def parse_request(self, request_data):
        request_line = request_data.splitlines()[0].decode()
        request_line = request_line.rstrip('\r\n')
        (self.request_method,
         self.path, self.request_version
         ) = request_line.split()

    def get_environ(self):
        env = {}

        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = BytesIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        # CGI variables
        env['REQUEST_METHOD'] = self.request_method
        env['PATH_INFO'] = self.path
        env['SERVER_NAME'] = self.server_name
        env['SERVER_PORT'] = str(self.server_port)
        return env

    def start_response(self, status, response_header, exc_info=None):
        date_time = datetime.now().strftime('%a, %d %m %Y, %H:%M:%S')
        server_headers = [
            ('Date', date_time),
            ('Server', 'WSGIServer 1.0'), ]

        self.header_set = [status, response_header + server_headers]

    def finish_response(self, result):
        try:
            status, response_header = self.header_set
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            for header in response_header:
                response += '{0}:{1}\r\n'.format(*header)
            response += '\r\n'
            response = response.encode()
            for data in result:
                response += data

            print('[{0} {1}]'.format(self.path, status))
            self.client_connect.sendall(response)
        finally:
            self.client_connect.close()


SERVER_ADDRESS = (HOST, PORT) = '', 5000


def maker_server(server_address, application):
    server = WSGIServer(server_address)
    server.get_app(application)
    return server


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(
            'Provide a WSGI application object must be as module:callable')
    app_path = sys.argv[1]
    module, app = app_path.split(':')
    module = __import__(module)
    application = getattr(module, app)
    httpd = maker_server(SERVER_ADDRESS, application)
    print('WSGIServer is servering on port {port}...\n'.format(port=PORT))
    httpd.server_forver()
