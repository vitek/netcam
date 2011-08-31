#!/usr/bin/env python
# Simple netcam server
import BaseHTTPServer

import gobject
import pygst
pygst.require("0.10")
import gst

class CameraSource(object):
    image = None
    cntr = 0
    def __init__(self, device=None):
        elements = []
        source = ['v4l2src', 'name=source']
        if device:
            source.append('device=%s' % device)
        elements.append(' '.join(source))
        elements.append('ffmpegcolorspace')
        elements.append('ffenc_mjpeg')
        #elements.append('queue')
        elements.append('appsink name=destination emit-signals=true')

        self.pipeline = gst.parse_launch(' ! '.join(elements))
        self.appsink = self.pipeline.get_by_name('destination')
        self.appsink.connect('new-buffer', self.on_new_buffer)
        self.pipeline.set_state(gst.STATE_PLAYING)

    def on_new_buffer(self, sink):
        self.image = self.appsink.emit('pull-buffer')

    def get_image(self):
        return self.image


class CameraHttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404, "Not found")
            return
        data = self.server.camera.get_image()
        if not data:
            self.send_error(404, "No image found")
            return
        self.send_response(200, "OK")
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)


class CameraHTTPServer(BaseHTTPServer.HTTPServer):
    def __init__(self, address, camera, loop):
        BaseHTTPServer.HTTPServer.__init__(
            self, address, CameraHttpRequestHandler)
        self.camera = camera
        gobject.io_add_watch(self.fileno(), gobject.IO_IN,
                             self.on_client_connected)

    def on_client_connected(self, io, event):
        self.handle_request()
        return True


def main():
    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-d", "--device", dest="device",
                      default="/dev/video0",
                      help="Specify v4l2 device", metavar="DEVICE")
    parser.add_option("-p", "--port",
                      type=int, dest="httpd_port", default=8000,
                      metavar="PORT",
                      help="Specify httpd port")
    parser.add_option("-l", "--listen", dest="httpd_address",
                      default="localhost",
                      help="Specify httpd listen address", metavar="ADDRESS")

    (options, args) = parser.parse_args()


    gobject.threads_init()
    loop = gobject.MainLoop()

    camera = CameraSource(device=options.device)
    httpd = CameraHTTPServer((options.httpd_address,
                              options.httpd_port), camera, loop)
    sa = httpd.socket.getsockname()
    print "Netcam server is listening on http://%s:%d/" % (sa[0], sa[1])
    loop.run()


if __name__ == "__main__":
    main()
