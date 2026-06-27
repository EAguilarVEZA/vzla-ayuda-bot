"""Built-in WhatsApp simulator served at /sim.

Lets you test the entire bot in a browser — no Twilio, no phone, no WhatsApp
number. It talks to the exact same handle() the real webhook uses, so what you
see here is what a real user gets. Add an Anthropic key to also test free-text
understanding + translation; without it the numeric menu + keywords still work.
"""

SIM_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ayuda Venezuela — Simulator</title>
<style>
  :root{--blue:#0033A0;--green:#dcf8c6;--bg:#0b1830;--ink:#13213f;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);font-family:'DM Sans',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:18px 12px 28px}
  .note{color:#cfe0ff;font-size:12.5px;max-width:380px;text-align:center;margin-bottom:12px}
  .phone{width:100%;max-width:400px;background:#e9e4dc;border-radius:18px;overflow:hidden;
    box-shadow:0 24px 60px -20px rgba(0,0,0,.6);display:flex;flex-direction:column;height:78vh}
  .top{background:var(--blue);color:#fff;padding:12px 14px;display:flex;align-items:center;gap:10px}
  .av{width:34px;height:34px;border-radius:50%;background:#fff;color:var(--blue);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}
  .top .nm{font-weight:600}.top .sub{font-size:11px;opacity:.85}
  .top .reset{margin-left:auto;font-size:11px;background:rgba(255,255,255,.18);border:none;color:#fff;border-radius:8px;padding:6px 9px;cursor:pointer}
  .msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background-image:linear-gradient(rgba(233,228,220,.6),rgba(233,228,220,.6))}
  .b{max-width:82%;padding:8px 11px;border-radius:12px;font-size:13.5px;line-height:1.5;white-space:pre-wrap;word-break:break-word;box-shadow:0 1px 1px rgba(0,0,0,.08)}
  .bot{align-self:flex-start;background:#fff;border-bottom-left-radius:3px}
  .me{align-self:flex-end;background:var(--green);border-bottom-right-radius:3px}
  .bar{display:flex;gap:8px;padding:10px;background:#f3efe9}
  .bar input{flex:1;border:1px solid #d6d0c6;border-radius:20px;padding:10px 14px;font-size:14px;outline:none}
  .bar button{background:var(--blue);color:#fff;border:none;border-radius:20px;padding:0 18px;font-weight:600;cursor:pointer}
  .quick{display:flex;gap:6px;flex-wrap:wrap;padding:8px 10px 0;background:#f3efe9}
  .quick button{font-size:12px;background:#fff;border:1px solid #d6d0c6;border-radius:14px;padding:5px 10px;cursor:pointer}
  .typing{align-self:flex-start;color:#888;font-size:12px;padding:4px 8px}
</style></head>
<body>
  <div class="note">🧪 Simulator — this is the real bot, no phone needed. Try the buttons or type anything (Spanish or English).</div>
  <div class="phone">
    <div class="top"><div class="av">AV</div>
      <div><div class="nm">Ayuda Venezuela</div><div class="sub" id="who">test user</div></div>
      <button class="reset" onclick="reset()">New tester</button>
    </div>
    <div class="msgs" id="msgs"></div>
    <div class="quick" id="quick"></div>
    <div class="bar"><input id="in" placeholder="Type a message…" autocomplete="off"
      onkeydown="if(event.key==='Enter')send()"><button onclick="send()">Send</button></div>
  </div>
<script>
let USER = 'sim:' + Math.random().toString(36).slice(2,9);
document.getElementById('who').textContent = USER;
const msgs=document.getElementById('msgs'), input=document.getElementById('in');
const QUICK=['hola','1','8','necesito','traduccion','remota','Venezuela','9','reportar','alertas','menu'];
document.getElementById('quick').innerHTML = QUICK.map(q=>`<button onclick="quick('${q}')">${q}</button>`).join('');

function bubble(text, who){const d=document.createElement('div');d.className='b '+who;d.textContent=text;msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;return d;}
function quick(q){input.value=q;send();}
async function send(){
  const text=input.value.trim(); if(!text) return;
  input.value=''; bubble(text,'me');
  const t=document.createElement('div'); t.className='typing'; t.textContent='…'; msgs.appendChild(t); msgs.scrollTop=msgs.scrollHeight;
  try{
    const r=await fetch('/sim/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:USER,body:text})});
    const j=await r.json(); t.remove(); bubble(j.reply||'(no reply)','bot');
  }catch(e){ t.remove(); bubble('Error: '+e.message,'bot'); }
}
function reset(){
  // wipe this tester's data, then start fresh
  fetch('/sim/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:USER,body:'BORRAR'})});
  USER='sim:'+Math.random().toString(36).slice(2,9); document.getElementById('who').textContent=USER; msgs.innerHTML='';
}
bubble('👋 Type "hola" or tap a button below to start.','bot');
</script>
</body></html>"""
