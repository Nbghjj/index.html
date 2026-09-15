from flask import Flask, render_template, Response, request, jsonify
import queue

# 1. መጀመሪያ app መፈጠር አለበት
app = Flask(__name__)

# 2. የ Queue እና ሌሎች አስፈላጊ ነገሮች መግለጫ
q = queue.Queue()

# 3. ከእዚያ በኋላ ነው @app.route የሚጀምረው
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def stream():
    def event_stream():
        while True:
            try:
                data = q.get(timeout=20)
                yield f"data: {data}\n\n"
            except:
                yield ": keep-alive\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
