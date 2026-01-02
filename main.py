import os
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from openai import OpenAI
from deepgram import DeepgramClient, LiveTranscriptionEvents
from deepgram.clients.live.v1 import LiveOptions

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
dg_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>עוזר פגישות טקטי</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        * { -webkit-tap-highlight-color: transparent; }
        .advice-box { transition: all 0.4s ease; }
        .advice-pulse { animation: glow 1.5s ease-in-out infinite alternate; border-color: #10b981 !important; }
        @keyframes glow { from { box-shadow: 0 0 5px #10b981, 0 0 10px #10b981; } to { box-shadow: 0 0 20px #10b981, 0 0 30px #10b981; } }
        .recording { animation: pulse-red 1s ease-in-out infinite; }
        @keyframes pulse-red { 0%, 100% { background-color: #dc2626; } 50% { background-color: #ef4444; } }
    </style>
</head>
<body class="bg-slate-950 text-white font-sans min-h-screen">
    <div class="max-w-lg mx-auto p-4 pb-20">
        <header class="text-center py-6 mb-4">
            <h1 class="text-2xl font-black text-emerald-400 tracking-tight">TACTICAL SIDEKICK</h1>
            <p class="text-slate-500 text-xs mt-1">עוזר פגישות AI בזמן אמת</p>
        </header>
        <div id="phase-brief" class="space-y-5">
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800">
                <label class="block text-sm font-semibold mb-3 text-slate-300">מי בפגישה?</label>
                <input id="participants" type="text" class="w-full bg-slate-950 rounded-xl p-3 text-white border border-slate-700 focus:border-emerald-500 outline-none" placeholder="למשל: אבי (מנהל), דנה (HR)">
            </div>
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800">
                <label class="block text-sm font-semibold mb-3 text-slate-300">מה המטרה שלך?</label>
                <textarea id="goal" rows="2" class="w-full bg-slate-950 rounded-xl p-3 text-white border border-slate-700 focus:border-emerald-500 outline-none" placeholder="למשל: לסגור העלאה בשכר של 15%"></textarea>
            </div>
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800">
                <label class="block text-sm font-semibold mb-3 text-slate-300">ממה אתה חושש?</label>
                <textarea id="challenges" rows="2" class="w-full bg-slate-950 rounded-xl p-3 text-white border border-slate-700 focus:border-emerald-500 outline-none" placeholder="למשל: יגידו שאין תקציב"></textarea>
            </div>
            <button onclick="goToCalibration()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl shadow-lg transition-all text-lg">המשך לזיהוי קול</button>
        </div>
        <div id="phase-calibrate" class="hidden text-center space-y-6">
            <div class="py-10">
                <div class="text-6xl mb-4">🎤</div>
                <h2 class="text-xl font-bold text-white mb-2">כיול קולי</h2>
                <p class="text-slate-400 text-sm px-4">דבר עכשיו במשך 5 שניות</p>
            </div>
            <div id="calibrationStatus" class="text-slate-500 text-sm">לחץ להתחלה</div>
            <button id="calibrateBtn" onclick="startCalibration()" class="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-4 rounded-xl shadow-lg transition-all">התחל כיול קולי</button>
            <button id="startMeetingBtn" onclick="startMeeting()" class="hidden w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl shadow-lg transition-all text-lg">התחל פגישה</button>
        </div>
        <div id="phase-live" class="hidden space-y-4">
            <div class="flex items-center justify-between px-2">
                <div class="flex items-center gap-2">
                    <div id="liveIndicator" class="w-3 h-3 rounded-full recording"></div>
                    <span class="text-xs text-slate-400">שידור חי</span>
                </div>
                <span id="speakerInfo" class="text-xs text-slate-500">ממתין...</span>
            </div>
            <div id="adviceBox" class="advice-box bg-gradient-to-br from-slate-900 to-slate-800 p-6 rounded-3xl min-h-[180px] flex items-center justify-center text-center border-2 border-slate-700">
                <p id="adviceText" class="text-xl font-bold text-emerald-50 leading-relaxed">המערכת מקשיבה...</p>
            </div>
            <div class="grid grid-cols-3 gap-2 text-center">
                <div class="bg-slate-900 p-3 rounded-xl"><div id="myTurns" class="text-lg font-bold text-emerald-400">0</div><div class="text-xs text-slate-500">תורות שלי</div></div>
                <div class="bg-slate-900 p-3 rounded-xl"><div id="otherTurns" class="text-lg font-bold text-sky-400">0</div><div class="text-xs text-slate-500">צד שני</div></div>
                <div class="bg-slate-900 p-3 rounded-xl"><div id="adviceCount" class="text-lg font-bold text-amber-400">0</div><div class="text-xs text-slate-500">עצות</div></div>
            </div>
            <details class="bg-slate-900 rounded-xl">
                <summary class="p-3 text-sm text-slate-400 cursor-pointer">תמליל מלא</summary>
                <div id="transcriptLog" class="p-3 pt-0 max-h-48 overflow-y-auto text-xs text-slate-500 space-y-1"></div>
            </details>
            <button onclick="endMeeting()" class="w-full bg-red-900 hover:bg-red-800 text-white py-3 rounded-xl text-sm">סיים פגישה</button>
        </div>
    </div>
    <script>
        let ws, mediaRecorder, audioStream;
        let stats = { myTurns: 0, otherTurns: 0, adviceCount: 0 };
        let brief = {};
        function goToCalibration() {
            brief = { participants: document.getElementById('participants').value, goal: document.getElementById('goal').value, challenges: document.getElementById('challenges').value };
            if (!brief.goal) { alert('נא להזין מטרה'); return; }
            document.getElementById('phase-brief').classList.add('hidden');
            document.getElementById('phase-calibrate').classList.remove('hidden');
        }
        async function startCalibration() {
            const btn = document.getElementById('calibrateBtn');
            const status = document.getElementById('calibrationStatus');
            try {
                audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                btn.disabled = true; btn.classList.add('opacity-50');
                let countdown = 5;
                status.innerText = 'מקליט... ' + countdown; status.classList.add('text-emerald-400');
                const interval = setInterval(() => {
                    countdown--;
                    if (countdown > 0) { status.innerText = 'מקליט... ' + countdown; }
                    else { clearInterval(interval); status.innerText = 'הכיול הושלם!'; btn.classList.add('hidden'); document.getElementById('startMeetingBtn').classList.remove('hidden'); }
                }, 1000);
            } catch (err) { status.innerText = 'שגיאה: נא לאשר גישה למיקרופון'; status.classList.add('text-red-400'); }
        }
        async function startMeeting() {
            document.getElementById('phase-calibrate').classList.add('hidden');
            document.getElementById('phase-live').classList.remove('hidden');
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
            ws.onopen = () => { ws.send(JSON.stringify({ type: 'setup', content: 'משתתפים: ' + brief.participants + '. מטרה: ' + brief.goal + '. אתגרים: ' + brief.challenges })); };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'advice') {
                    document.getElementById('adviceText').innerHTML = data.content;
                    document.getElementById('adviceBox').classList.add('advice-pulse');
                    stats.adviceCount++; document.getElementById('adviceCount').innerText = stats.adviceCount;
                    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
                    setTimeout(() => document.getElementById('adviceBox').classList.remove('advice-pulse'), 3000);
                }
                if (data.type === 'transcript') {
                    const log = document.getElementById('transcriptLog');
                    const isMe = data.content.startsWith('אני:');
                    log.innerHTML += '<div class="' + (isMe ? 'text-emerald-400' : 'text-sky-400') + '">' + data.content + '</div>';
                    log.scrollTop = log.scrollHeight;
                    if (isMe) { stats.myTurns++; document.getElementById('myTurns').innerText = stats.myTurns; }
                    else { stats.otherTurns++; document.getElementById('otherTurns').innerText = stats.otherTurns; }
                    document.getElementById('speakerInfo').innerText = isMe ? 'אתה מדבר' : 'צד שני';
                }
            };
            mediaRecorder = new MediaRecorder(audioStream);
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data); };
            mediaRecorder.start(1500);
        }
        function endMeeting() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
            if (audioStream) audioStream.getTracks().forEach(track => track.stop());
            if (ws) ws.close();
            document.getElementById('liveIndicator').classList.remove('recording');
            document.getElementById('liveIndicator').classList.add('bg-slate-600');
            alert('סיכום: תורות שלך: ' + stats.myTurns + ', צד שני: ' + stats.otherTurns + ', עצות: ' + stats.adviceCount);
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_root():
    return HTMLResponse(HTML_TEMPLATE)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = {"brief": "", "transcript": [], "user_speaker_id": None, "calibration_count": 0}
    loop = asyncio.get_event_loop()
    
    options = LiveOptions(model="nova-2", language="he", smart_format=True, diarize=True, punctuate=True, interim_results=False)
    dg_connection = dg_client.listen.live.v("1")
    
    def on_transcript(self, result, **kwargs):
        try:
            transcript = result.channel.alternatives[0].transcript
            if not transcript or len(transcript.strip()) < 2: return
            words = result.channel.alternatives[0].words
            speaker = words[0].speaker if words else 0
            if session["user_speaker_id"] is None:
                session["calibration_count"] += 1
                if session["calibration_count"] >= 1: session["user_speaker_id"] = speaker
            is_me = (speaker == session["user_speaker_id"])
            role = "אני" if is_me else "צד שני"
            line = f"{role}: {transcript}"
            session["transcript"].append(line)
            asyncio.run_coroutine_threadsafe(websocket.send_json({"type": "transcript", "content": line}), loop)
            should_advise = (not is_me) or (len(session["transcript"]) % 5 == 0)
            if should_advise and session["brief"]:
                recent = "\n".join(session["transcript"][-8:])
                prompt = f"אתה יועץ טקטי. בריף: {session['brief']}. תן עצה קצרה (עד 15 מילים) בעברית."
                try:
                    response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": recent}], max_tokens=100)
                    advice = response.choices[0].message.content.strip()
                    asyncio.run_coroutine_threadsafe(websocket.send_json({"type": "advice", "content": advice}), loop)
                except Exception as e: print(f"OpenAI error: {e}")
        except Exception as e: print(f"Error: {e}")
    
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    
    try:
        dg_connection.start(options)
        while True:
            data = await websocket.receive()
            if "text" in data:
                msg = json.loads(data["text"])
                if msg["type"] == "setup": session["brief"] = msg["content"]; session["transcript"] = []
            elif "bytes" in data: dg_connection.send(data["bytes"])
    except Exception as e: print(f"WS error: {e}")
    finally: dg_connection.finish()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
