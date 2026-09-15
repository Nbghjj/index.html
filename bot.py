# በ bot.py ውስጥ ያለው የ stream ተግባርህ እንደዚህ መስተካከል አለበት፦
@app.route('/events')  # ወይም /stream
def stream():
    def event_stream():
        while True:
            try:
                # ለ 20 ሰከንድ ዳታ ካላገኘ እራሱን ያድሳል
                data = q.get(timeout=20)
                yield f"data: {data}\n\n"
            except:
                # በየ 20 ሰከንዱ Ping ይልካል (ለእረፍት እንዳይዘጋ)
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
