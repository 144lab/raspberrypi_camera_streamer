# Raspberry Pi camera streaming tool
# Source code from Yasin Arabi
# http://yasinam.ir/

import io
import subprocess
import logging
import socketserver
from threading import Condition
from http import server
from time import sleep

stream_status = False
stream_path = ''

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == stream_path:
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()

            proc = subprocess.Popen('libcamera-vid -n -t 0 --codec mjpeg -o -', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print('start')
            buffer = io.BytesIO()
            # sleep(5)
            # print(proc.pid, proc.returncode)
            # print(proc.stderr.readlines())
            try:
                framecount = 0
                while True:
                    frame = None
                    while True:
                        # print('read')
                        buf = proc.stdout.read1()
                        # print(len(buf), buf[:16])
                        index = buf.find(b'\xff\xd8')
                        if index>0:
                            buffer.write(buf[:index])
                        # if buf.startswith(b'\xff\xd8'):
                            framecount+=1
                            print('Frames', framecount)
                            # New frame, copy the existing buffer's content
                            buffer.truncate()
                            frame = buffer.getvalue()
                            buffer.seek(0)
                            buffer.write(buf[index:])
                            if framecount==1:
                                pass
                            else:
                                break
                        else:
                            buffer.write(buf)
                    # print('New Frame')
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def run(listen, port, path, width, height, framerate, quality, rotation, vflip, hflip, **kwargs):
    global output, server, stream_status, stream_path
    stream_path = path

    # output = StreamingOutput()
    # camera.resolution = (width,height)
    # camera.framerate = framerate
    # camera.rotation = rotation
    # camera.hflip = hflip
    # camera.vflip = vflip
    # camera.start_recording(output, format='mjpeg', quality=max(min(quality,100),1))
    # print(camera.frame, camera.resolution,camera.framerate,camera.vflip,camera.hflip,camera.rotation)
    try:
        address = (listen, port)
        stream_status = True
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        pass
        # camera.stop_recording()

def status():
    global stream_status
    return stream_status

def stop():
    global server, stream_status
    stream_status = False
    server.shutdown()
    server.server_close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=str, default="")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--path", type=str, default="/stream.mjpg")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--framerate", type=int, default=30)
    parser.add_argument("--quality", type=int, default=100)
    parser.add_argument("--hflip", action='store_true')
    parser.add_argument("--vflip", action='store_true')
    parser.add_argument("--rotation", type=int, default=0)
    args = parser.parse_args()
    run(**vars(args))
