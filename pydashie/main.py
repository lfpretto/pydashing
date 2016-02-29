import os
import logging
from flask import Flask, render_template, Response, send_from_directory, request, current_app

app = Flask(__name__)
logging.basicConfig()
log = logging.getLogger(__name__)


@app.route("/")
def main():
    return render_template('main.html', title='pyDashie')
    
@app.route("/dashboard/<dashlayout>/")
def custom_layout(dashlayout):
    return render_template('%s.html'%dashlayout, title='pyDashie')

@app.route("/assets/application.js")
def javascripts():
    if not hasattr(current_app, 'javascripts'):
        import coffeescript
        scripts = [
            'assets/javascripts/jquery.js',
            'assets/javascripts/es5-shim.js',
            'assets/javascripts/d3.v2.min.js',
            'assets/javascripts/batman.js',
            'assets/javascripts/batman.jquery.js',
            'assets/javascripts/jquery.gridster.js',
            'assets/javascripts/jquery.leanModal.min.js',
            'assets/javascripts/dashing.coffee',
            'assets/javascripts/dashing.gridster.coffee',
            'assets/javascripts/jquery.knob.js',
            'assets/javascripts/rickshaw.min.js',
            'assets/javascripts/application.coffee',
            #'assets/javascripts/app.js',

            'widgets/clock/clock.coffee',
            'widgets/number/number.coffee',
        ]
        nizzle = True
        if not nizzle:
            scripts = ['assets/javascripts/application.js']

        output = []
        for path in scripts:
            output.append('// JS: %s\n' % path)
            if '.coffee' in path:
                log.info('Compiling Coffee for %s ' % path)
                contents = str(coffeescript.compile_file(path))
                print '-------------------------'
                print contents
            else:
                f = open(path)
                contents = f.read()
                f.close()
            output.append(contents)

        if not nizzle:
            f = open('/tmp/foo.js', 'w')
            for o in output:
                print >> f, o
            f.close()

            f = open('/tmp/foo.js', 'rb')
            output = f.read()
            f.close()
            current_app.javascripts = output
        else:
            #print output
            current_app.javascripts = '\n'.join(output)

    return Response(current_app.javascripts, mimetype='application/javascript')

@app.route('/assets/application.css')
def application_css():
    scripts = [
        'assets/stylesheets/application.css',
    ]
    output = ''
    for path in scripts:
        output += open(path).read()
    return Response(output, mimetype='text/css')

@app.route('/assets/images/<path:filename>')
def send_static_img(filename):
    directory = os.path.join('assets', 'images')
    return send_from_directory(directory, filename)

@app.route('/views/<widget_name>.html')
def widget_html(widget_name):
    html = '%s.html' % widget_name
    path = os.path.join('widgets', widget_name, html)
    if os.path.isfile(path):
        f = open(path)
        contents = f.read()
        f.close()
        return contents

import Queue
import json
import datetime

class ConnectionStreams:
    def __init__(self):
        self.MAX_QUEUE_LENGTH = 20
        self.MAX_LAST_EVENTS = 20
        self.events_queue = {}
        self.last_events = ['{}'] * self.MAX_LAST_EVENTS
        self.using_events = True
        self.stopped = False

    def send(self, body):
        formatted_json = 'data: %s\n\n' % (json.dumps(body))
        for event_queue in self.events_queue.values():
            event_queue.put(formatted_json)
        self.last_events.append(formatted_json)
        self.last_events.pop(0)
        return formatted_json

    def openStream(self, streamID):
        current_event_queue = Queue.Queue()
        self.events_queue[streamID] = current_event_queue
        #Start the newly connected client off by pushing the current last events
        for event in self.last_events:
            current_event_queue.put(event)
        while not self.stopped:
            try:
                data = current_event_queue.get(timeout=0.1)
                yield data
            except Queue.Empty:
                #this makes the server quit nicely - previously the queue threads would block and never exit. This makes it keep checking for dead application
                pass

    def closeStream(self, streamID):
        del self.events_queue[streamID]

    def stop(self):
        self.stopped = True

    def __len__(self):
        return len(self.events_queue)


xyzzy = ConnectionStreams()



@app.route('/add/<widget_id>/<nValue>')
def addValue(widget_id, nValue):
    body = dict()
    body['current'] = nValue
    body['id'] = widget_id
    body['updatedAt'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S +0000')
    return Response(xyzzy.send(body), mimetype='text/json')

@app.route('/events')
def events():
    event_stream_port = request.environ['REMOTE_PORT']
    current_app.logger.info('New Client %s connected. Total Clients: %s' % (event_stream_port, len(xyzzy)))
    #current_event_queue = xyzzy.openStream(event_stream_port)
    return Response(xyzzy.openStream(event_stream_port), mimetype='text/event-stream')


'''
def other():
    event_stream_port = 0
    if xyzzy.using_events:
        current_event_queue = Queue.Queue()
        xyzzy.events_queue[event_stream_port] = current_event_queue
        current_app.logger.info('New Client %s connected. Total Clients: %s' % (event_stream_port, len(xyzzy.events_queue)))
        #Start the newly connected client off by pushing the current last events
        for event in xyzzy.last_events.values():
            current_event_queue.put(event)
        return Response(pop_queue(current_event_queue), mimetype='text/event-stream')
    return Response(xyzzy.last_events.values(), mimetype='text/event-stream')


def pop_queue(current_event_queue):
    while not xyzzy.stopped:
        try:
            data = current_event_queue.get(timeout=0.1)
            yield data
        except Queue.Empty:
            pass #this makes the server quit nicely - previously the queue threads would block and never exit.
            # This makes it keep checking for dead application
'''

def purge_streams():
    big_queues = [port for port, queue in xyzzy.events_queue if len(queue) > xyzzy.MAX_QUEUE_LENGTH]
    for big_queue in big_queues:
        current_app.logger.info('Client %s is stale. Disconnecting. Total Clients: %s' %
                                (big_queue, len(xyzzy.events_queue)))
        del queue[big_queue]






        
def close_stream(*args, **kwargs):
    event_stream_port = args[2][1]
    xyzzy.closeStream(event_stream_port)
    log.info('Client %s disconnected. Total Clients: %s' % (event_stream_port, len(xyzzy.events_queue)))





def run_sample_app():
    import SocketServer
    SocketServer.BaseServer.handle_error = close_stream
    import example_app
    example_app.run(app, xyzzy)


if __name__ == "__main__":
    run_sample_app()
