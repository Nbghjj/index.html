@app.route('/stream')
def stream():
    def event_stream():
        # የካርድ መቆለፍ / ማስመር መረጃዎች
        yield f"data: {data}\n\n"
        
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Render/Nginx እንዳይዘገየው ይረዳል
            'Connection': 'keep-alive'
        }
    )
