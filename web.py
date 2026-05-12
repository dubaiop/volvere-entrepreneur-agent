"""Entrepreneur Agent — FastAPI web dashboard."""

from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import io

from config import PORT, COMPANY_NAME, TELEGRAM_BOT_TOKEN
from agent import run_skill, chat, clear_memory
from skills.prompts import SKILL_MAP
from database import init_db, get_opportunities, get_audit_log, get_metrics

app = FastAPI(title=f"{COMPANY_NAME} Entrepreneur Agent", version="1.0.0")
_tg_app = None

SKILL_COLORS = {
    "problem-scanner": "#f59e0b",
    "opportunity-validator": "#ef4444",
    "business-model-designer": "#6366f1",
    "market-sizer": "#3b82f6",
    "competition-mapper": "#f97316",
    "mvp-planner": "#10b981",
    "pitch-crafter": "#8b5cf6",
    "trend-spotter": "#06b6d4",
}


@app.on_event("startup")
async def startup():
    global _tg_app
    init_db()
    from scheduler import start_scheduler
    start_scheduler()

    if TELEGRAM_BOT_TOKEN:
        try:
            from telegram_bot import build_application
            import os
            _tg_app = build_application()
            await _tg_app.initialize()
            domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
            if domain:
                await _tg_app.bot.set_webhook(f"https://{domain}/telegram/webhook")
            await _tg_app.start()
        except Exception as e:
            print(f"Telegram init error: {e}")


@app.on_event("shutdown")
async def shutdown():
    if _tg_app:
        await _tg_app.stop()
        await _tg_app.shutdown()


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not _tg_app:
        return {"ok": False}
    from telegram import Update
    data = await request.json()
    update = Update.de_json(data, _tg_app.bot)
    await _tg_app.process_update(update)
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    metrics = get_metrics()
    total_runs = metrics.get("total", 0)
    problems_scanned = metrics.get("count_problem-scanner", 0)
    ideas_validated = metrics.get("count_opportunity-validator", 0)
    pitches_crafted = metrics.get("count_pitch-crafter", 0)

    skill_cards = ""
    for sk_id, sk in SKILL_MAP.items():
        color = SKILL_COLORS.get(sk_id, "#6366f1")
        skill_cards += f"""
        <div class="skill-card" onclick="selectSkill('{sk_id}')">
          <div class="skill-dot" style="background:{color}"></div>
          <div><div class="skill-name">{sk['name']}</div><div class="skill-desc">{sk['description']}</div></div>
        </div>"""

    today = datetime.now().strftime("%A, %B %d")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{COMPANY_NAME} Entrepreneur Agent</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#07070f;--s:#0e0e1c;--s2:#141428;--b:#1a1a30;--b2:#242445;--a:#f59e0b;--a2:#fbbf24;--green:#10b981;--red:#ef4444;--purple:#8b5cf6;--text:#f0f0ff;--m:#55557a;--m2:#8080a8;--r:12px}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px}}
    header{{border-bottom:1px solid var(--b);padding:0 40px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:rgba(7,7,15,.96);backdrop-filter:blur(16px);z-index:100}}
    .logo{{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;text-decoration:none;color:var(--text)}}
    .logo-dot{{width:10px;height:10px;border-radius:50%;background:var(--a);box-shadow:0 0 12px var(--a)}}
    .nav a{{color:var(--m2);text-decoration:none;font-size:13px;margin-left:24px}}
    .nav a:hover{{color:var(--text)}}
    main{{max-width:1280px;margin:0 auto;padding:32px 40px 80px;display:grid;grid-template-columns:1fr 360px;gap:32px}}
    .left{{display:flex;flex-direction:column;gap:28px}}
    .right{{display:flex;flex-direction:column;gap:20px;position:sticky;top:80px;max-height:calc(100vh - 100px)}}
    .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
    .m-card{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);padding:18px 20px}}
    .m-val{{font-size:26px;font-weight:700}}
    .m-lbl{{font-size:11px;color:var(--m);text-transform:uppercase;letter-spacing:.5px;margin-top:4px}}
    .m-sub{{font-size:12px;color:var(--a2);margin-top:3px}}
    .section-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--m);margin-bottom:14px}}
    .skill-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .skill-card{{display:flex;align-items:flex-start;gap:12px;background:var(--s);border:1px solid var(--b);border-radius:var(--r);padding:14px 16px;cursor:pointer;transition:border-color .15s,background .15s}}
    .skill-card:hover,.skill-card.active{{border-color:var(--a);background:rgba(245,158,11,.06)}}
    .skill-dot{{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0}}
    .skill-name{{font-weight:600;font-size:13px}}
    .skill-desc{{font-size:12px;color:var(--m2);margin-top:2px;line-height:1.4}}
    .runner{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);overflow:hidden}}
    .runner-hdr{{padding:14px 20px;border-bottom:1px solid var(--b);background:var(--s2);font-weight:600;font-size:14px;display:flex;align-items:center;gap:8px}}
    .runner-body{{padding:20px;display:flex;flex-direction:column;gap:12px}}
    .runner-body label{{font-size:12px;color:var(--m2);font-weight:500;display:block;margin-bottom:4px}}
    .runner-body select,.runner-body textarea,.runner-body input{{width:100%;background:var(--bg);border:1px solid var(--b2);border-radius:8px;color:var(--text);padding:10px 12px;font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}}
    .runner-body select:focus,.runner-body textarea:focus,.runner-body input:focus{{border-color:var(--a)}}
    .runner-body textarea{{resize:vertical;min-height:90px}}
    .run-btn{{background:var(--a);color:#07070f;border:none;border-radius:8px;padding:11px;font-size:13px;font-weight:700;cursor:pointer;width:100%;transition:opacity .15s}}
    .run-btn:hover{{opacity:.85}}
    .run-btn:disabled{{opacity:.4;cursor:not-allowed}}
    .result{{background:var(--bg);border:1px solid var(--b);border-radius:8px;padding:16px;font-size:13px;line-height:1.7;white-space:pre-wrap;display:none;max-height:500px;overflow-y:auto}}
    .result.show{{display:block}}
    .chat-panel{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);display:flex;flex-direction:column;flex:1;min-height:0}}
    .chat-hdr{{padding:14px 18px;border-bottom:1px solid var(--b);background:var(--s2);border-radius:var(--r) var(--r) 0 0;display:flex;align-items:center;gap:10px}}
    .online{{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);flex-shrink:0}}
    .chat-title{{font-weight:600;font-size:13px}}
    .chat-sub{{font-size:11px;color:var(--m2)}}
    .chat-msgs{{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;min-height:200px;max-height:400px}}
    .msg{{padding:10px 13px;border-radius:10px;font-size:13px;line-height:1.6;white-space:pre-wrap;max-width:92%}}
    .msg.user{{background:rgba(245,158,11,.18);border:1px solid rgba(245,158,11,.3);align-self:flex-end;border-radius:10px 10px 2px 10px}}
    .msg.bot{{background:var(--s2);border:1px solid var(--b2);align-self:flex-start;border-radius:10px 10px 10px 2px}}
    .msg.sys{{color:var(--m);font-size:12px;text-align:center;align-self:center;background:none;border:none}}
    .chat-input-row{{padding:10px;border-top:1px solid var(--b);display:flex;gap:8px}}
    .chat-in{{flex:1;background:var(--bg);border:1px solid var(--b2);border-radius:8px;color:var(--text);padding:9px 12px;font-size:13px;font-family:inherit;outline:none;resize:none;transition:border-color .15s}}
    .chat-in:focus{{border-color:var(--a)}}
    .send-btn{{background:var(--a);color:#07070f;border:none;border-radius:8px;padding:9px 14px;cursor:pointer;transition:opacity .15s;flex-shrink:0;font-weight:700}}
    .send-btn:disabled{{opacity:.4}}
    .spinner{{display:inline-block;width:13px;height:13px;border:2px solid rgba(245,158,11,.3);border-top-color:var(--a2);border-radius:50%;animation:spin .7s linear infinite;margin-right:6px;vertical-align:middle}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    @media(max-width:960px){{main{{grid-template-columns:1fr}}.right{{position:static}}.metrics{{grid-template-columns:repeat(2,1fr)}}.skill-grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <a class="logo" href="/"><span class="logo-dot"></span>{COMPANY_NAME} Entrepreneur Agent</a>
  <nav class="nav">
    <a href="#skills">Skills</a><a href="/audit">Audit</a><a href="/docs">API</a>
  </nav>
</header>
<main>
  <div class="left">
    <div>
      <div style="margin-bottom:8px;color:var(--m2);font-size:13px">{today}</div>
      <h1 style="font-size:28px;font-weight:700;margin-bottom:4px">Entrepreneur Intelligence Engine</h1>
      <p style="color:var(--m2)">8 AI skills. Find real problems. Validate fast. Build legendary companies.</p>
    </div>

    <div class="metrics">
      <div class="m-card"><div class="m-val">{total_runs}</div><div class="m-lbl">Total Analyses</div></div>
      <div class="m-card"><div class="m-val">{problems_scanned}</div><div class="m-lbl">Problems Scanned</div></div>
      <div class="m-card"><div class="m-val">{ideas_validated}</div><div class="m-lbl">Ideas Validated</div></div>
      <div class="m-card"><div class="m-val">{pitches_crafted}</div><div class="m-lbl">Pitches Crafted</div></div>
    </div>

    <div id="skills">
      <div class="section-label">8 Entrepreneur Skills</div>
      <div class="skill-grid">{skill_cards}</div>
    </div>

    <div class="runner" id="runner">
      <div class="runner-hdr">⚡ Run a Skill</div>
      <div class="runner-body">
        <div>
          <label>Skill</label>
          <select id="skillSel">{"".join(f'<option value="{sk_id}">{SKILL_MAP[sk_id]["name"]}</option>' for sk_id in SKILL_MAP)}</select>
        </div>
        <div>
          <label>Focus (industry, geography, stage)</label>
          <input type="text" id="ctx" placeholder="e.g. Dubai real estate, B2B SaaS, MENA fintech"/>
        </div>
        <div>
          <label>Input</label>
          <textarea id="inp" placeholder="Describe an industry, problem, idea, competitor, trend..."></textarea>
        </div>
        <button class="run-btn" id="runBtn" onclick="runSkill()">Analyze</button>
        <div class="result" id="res"></div>
      </div>
    </div>
  </div>

  <div class="right">
    <div class="chat-panel">
      <div class="chat-hdr">
        <span class="online"></span>
        <div><div class="chat-title">Entrepreneur AI Chat</div><div class="chat-sub">Share any idea — I'll challenge and build on it</div></div>
      </div>
      <div class="chat-msgs" id="msgs">
        <div class="msg sys">Tell me an industry you're curious about or an idea you want to test.</div>
      </div>
      <div class="chat-input-row">
        <label title="Upload PDF, TXT, or DOCX" style="cursor:pointer;background:var(--b2);border:1px solid var(--b2);border-radius:8px;padding:9px 10px;flex-shrink:0;font-size:14px;display:flex;align-items:center" id="uploadLabel">
          📎<input type="file" id="fileIn" accept=".pdf,.txt,.md,.docx" style="display:none" onchange="uploadFile()"/>
        </label>
        <textarea class="chat-in" id="chatIn" rows="1" placeholder="Message or drop a PDF..." onkeydown="handleKey(event)"></textarea>
        <button class="send-btn" id="sendBtn" onclick="send()">➤</button>
      </div>
    </div>
  </div>
</main>

<script>
const sid = 'web-' + Math.random().toString(36).slice(2,8);

function selectSkill(id){{
  document.getElementById('skillSel').value=id;
  document.querySelectorAll('.skill-card').forEach(c=>c.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('runner').scrollIntoView({{behavior:'smooth',block:'center'}});
}}

async function runSkill(){{
  const skill=document.getElementById('skillSel').value;
  const input=document.getElementById('inp').value.trim();
  const context=document.getElementById('ctx').value.trim();
  if(!input){{alert('Enter your input.');return;}}
  const btn=document.getElementById('runBtn'),res=document.getElementById('res');
  btn.disabled=true;btn.innerHTML='<span class="spinner"></span>Analyzing...';
  res.className='result show';res.textContent='Thinking...';
  try{{
    const r=await fetch('/skill/sync',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{skill,input,context,session_id:sid}})}});
    const d=await r.json();res.textContent=d.result||d.detail||'No result.';
  }}catch(e){{res.textContent='Error: '+e.message;}}
  btn.disabled=false;btn.innerHTML='Analyze';
}}

function handleKey(e){{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();send();}}}}

function addMsg(role,text){{
  const d=document.createElement('div');d.className='msg '+role;d.textContent=text;
  const m=document.getElementById('msgs');m.appendChild(d);m.scrollTop=m.scrollHeight;return d;
}}

async function send(){{
  const inp=document.getElementById('chatIn');
  const msg=inp.value.trim();if(!msg)return;
  inp.value='';addMsg('user',msg);
  const btn=document.getElementById('sendBtn');btn.disabled=true;
  const ph=addMsg('bot','...');
  try{{
    const r=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg,session_id:sid}})}});
    const d=await r.json();ph.textContent=d.reply||d.detail||'No response.';
  }}catch(e){{ph.textContent='Error: '+e.message;}}
  btn.disabled=false;
}}

async function uploadFile(){{
  const file=document.getElementById('fileIn').files[0];
  if(!file)return;
  const label=document.getElementById('uploadLabel');
  label.textContent='⏳';
  addMsg('user',`📎 ${{file.name}}`);
  const form=new FormData();form.append('file',file);
  try{{
    const r=await fetch('/upload',{{method:'POST',body:form}});
    const d=await r.json();
    if(d.error){{addMsg('bot','Upload error: '+d.error);}}
    else{{
      const ph=addMsg('bot','...');
      const r2=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:d.prompt,session_id:sid}})}});
      const d2=await r2.json();ph.textContent=d2.reply||d2.detail||'No response.';
    }}
  }}catch(e){{addMsg('bot','Error: '+e.message);}}
  label.innerHTML='📎<input type="file" id="fileIn" accept=".pdf,.txt,.md,.docx" style="display:none" onchange="uploadFile()"/>';
}}
</script>
</body>
</html>"""


class ChatReq(BaseModel):
    message: str
    session_id: Optional[str] = "web"


class SkillReq(BaseModel):
    skill: str
    input: str
    context: Optional[str] = ""
    session_id: Optional[str] = "web"


@app.post("/chat")
def chat_endpoint(req: ChatReq):
    try:
        return {"reply": chat(req.message, req.session_id or "web")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/skill/sync")
def skill_sync(req: SkillReq):
    if req.skill not in SKILL_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown skill '{req.skill}'")
    try:
        return {"skill": req.skill, "result": run_skill(req.skill, req.input, req.context or "", req.session_id or "web")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit")
def audit():
    return get_audit_log(limit=100)


@app.get("/opportunities")
def opportunities():
    return get_opportunities(limit=100)


@app.get("/metrics")
def metrics_endpoint():
    return get_metrics()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Extract text from PDF/TXT/DOCX and return a prompt ready for the chat endpoint."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()

    try:
        if ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext in ("txt", "md"):
            text = content.decode("utf-8", errors="ignore")
        elif ext == "docx":
            try:
                import zipfile, re
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", xml)
                text = re.sub(r"\s+", " ", text).strip()
            except Exception:
                return {"error": "Could not parse DOCX file."}
        else:
            return {"error": f"Unsupported file type '.{ext}'. Upload PDF, TXT, or DOCX."}

        text = text.strip()
        if not text:
            return {"error": "File appears to be empty or unreadable."}

        # Truncate to ~6000 chars to stay within context limits
        truncated = text[:6000] + ("\n\n[truncated...]" if len(text) > 6000 else "")

        prompt = (
            f"I've uploaded a file: **{filename}**\n\n"
            f"Here is its content:\n\n---\n{truncated}\n---\n\n"
            f"Apply your entrepreneur framework to this. Find the hidden opportunity, destroy the assumptions, and tell me what's actually worth building here."
        )
        return {"filename": filename, "chars": len(text), "prompt": prompt}

    except Exception as e:
        return {"error": str(e)}


@app.post("/pipeline/run")
def run_pipeline():
    """Manually trigger the full opportunity pipeline (find → validate → model → outreach → Telegram)."""
    import threading
    from scheduler import daily_full_pipeline
    threading.Thread(target=daily_full_pipeline, daemon=True).start()
    return {"status": "started", "message": "Pipeline running in background — check Telegram for results."}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=PORT, reload=False)
