# -*- coding: utf-8 -*-
"""
Génération HTML pour la tablette Pepper — design premium animé
"""
from config import API_CONFIG, SHOW_TABLET_CALL_BUTTON
from utils.helpers import (
    force_utf8,
    escape_html,
    transliterate_to_ascii,
    get_local_ip_for_robot,
)

# ---------------------------------------------------------------------------
# Template HTML principal (les accolades CSS/JS sont doublées {{ }})
# Les slots Python sont : {title} {message} {status_html} {subtitle_html}
#                         {mic_html} {call_slot} {qr_slot} {chat_slot}
#                         {scripts_extra} {mic_script}
# ---------------------------------------------------------------------------
_HTML = u"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Pepper Hotel</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;height:100%;overflow:hidden;
  font-family:'Segoe UI',system-ui,Arial,sans-serif;
  background:#04040f;color:#fff;
  -webkit-tap-highlight-color:transparent}}

/* ═══════════════════════════════════════════
   FOND : canvas particules + aurora
═══════════════════════════════════════════ */
#bgCanvas{{position:fixed;inset:0;z-index:0}}

.aurora{{position:fixed;inset:0;z-index:1;pointer-events:none;overflow:hidden}}
.aurora-blob{{
  position:absolute;border-radius:50%;
  filter:blur(90px);opacity:0.13;
  animation:blobMove ease-in-out infinite alternate}}
.ab1{{width:420px;height:420px;
  background:radial-gradient(circle,#7c3aed,transparent 70%);
  top:-120px;left:-100px;animation-duration:14s}}
.ab2{{width:380px;height:380px;
  background:radial-gradient(circle,#2563eb,transparent 70%);
  bottom:-100px;right:-80px;animation-duration:18s;animation-delay:-7s}}
.ab3{{width:320px;height:320px;
  background:radial-gradient(circle,#0e7490,transparent 70%);
  top:30%;left:55%;opacity:0.09;animation-duration:12s;animation-delay:-4s}}
.ab4{{width:260px;height:260px;
  background:radial-gradient(circle,#9333ea,transparent 70%);
  top:60%;left:10%;opacity:0.08;animation-duration:20s;animation-delay:-10s}}
@keyframes blobMove{{
  0%  {{transform:translate(0,0) scale(1)}}
  50% {{transform:translate(25px,-35px) scale(1.12)}}
  100%{{transform:translate(-18px,22px) scale(0.92)}}
}}

/* ═══════════════════════════════════════════
   LAYOUT
═══════════════════════════════════════════ */
.wrap{{
  position:relative;z-index:2;
  display:flex;flex-direction:column;
  height:100vh;padding:13px 13px 12px;gap:9px;
  animation:pageIn .7s ease both}}
@keyframes pageIn{{
  from{{opacity:0;transform:translateY(14px)}}
  to  {{opacity:1;transform:translateY(0)}}
}}

/* ═══════════════════════════════════════════
   HEADER
═══════════════════════════════════════════ */
.hdr{{
  display:flex;align-items:center;gap:11px;
  flex-shrink:0;
  animation:slideDown .6s .05s ease both}}
@keyframes slideDown{{
  from{{opacity:0;transform:translateY(-14px)}}
  to  {{opacity:1;transform:translateY(0)}}
}}

/* Avatar + anneau tournant */
.av-wrap{{position:relative;width:62px;height:62px;flex-shrink:0}}
.av-ring{{
  position:absolute;inset:-3px;border-radius:50%;
  background:conic-gradient(from 0deg,#6366f1,#a78bfa,#38bdf8,#4ade80,#6366f1);
  animation:spinRing 3.5s linear infinite;z-index:0}}
@keyframes spinRing{{to{{transform:rotate(360deg)}}}}
.av-inner{{
  position:relative;z-index:1;
  width:100%;height:100%;
  background:linear-gradient(145deg,#1e1b4b,#312e81);
  border-radius:50%;border:3px solid #04040f;
  display:flex;align-items:center;justify-content:center;
  font-size:29px;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.5)}}

/* Nom hôtel shimmer */
.hdr-info{{flex:1;min-width:0}}
.hdr-name{{
  font-size:23px;font-weight:900;letter-spacing:.4px;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;
  background:linear-gradient(90deg,#c7d2fe 0%,#a5b4fc 18%,#f0abfc 36%,#bae6fd 54%,#a5b4fc 72%,#c7d2fe 90%);
  background-size:220% auto;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:textShimmer 5s linear infinite}}
@keyframes textShimmer{{to{{background-position:220% center}}}}
.hdr-sub{{
  font-size:10px;color:rgba(255,255,255,.38);
  letter-spacing:1.8px;text-transform:uppercase;margin-top:3px}}

/* Horloge */
.clock{{text-align:right;flex-shrink:0}}
.clk-time{{
  font-size:21px;font-weight:700;color:#e0e7ff;
  letter-spacing:2px;font-variant-numeric:tabular-nums}}
.clk-date{{font-size:9.5px;color:rgba(255,255,255,.35);letter-spacing:.4px;margin-top:2px}}

/* ═══════════════════════════════════════════
   BADGE STATUT
═══════════════════════════════════════════ */
.status-badge{{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(255,255,255,.06);backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,.13);border-radius:40px;
  padding:7px 16px;font-size:12.5px;font-weight:500;
  color:rgba(255,255,255,.85);
  flex-shrink:0;align-self:flex-start;
  box-shadow:0 4px 16px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.08);
  animation:slideDown .6s .15s ease both}}
.sdot{{
  width:9px;height:9px;background:#4ade80;border-radius:50%;
  box-shadow:0 0 8px #4ade80,0 0 18px rgba(74,222,128,.45);
  animation:pulseDot 2s ease-in-out infinite}}
@keyframes pulseDot{{
  0%,100%{{transform:scale(1);opacity:1}}
  50%    {{transform:scale(1.5);opacity:.5}}
}}

/* ═══════════════════════════════════════════
   CARTE MESSAGE
═══════════════════════════════════════════ */
.msg-card{{
  position:relative;
  background:rgba(255,255,255,.055);backdrop-filter:blur(18px);
  border-radius:22px;padding:17px 19px;flex-shrink:0;overflow:hidden;
  box-shadow:0 8px 32px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.07);
  animation:slideDown .6s .25s ease both}}
/* Bord shimmer */
.msg-card::before{{
  content:'';position:absolute;inset:0;border-radius:22px;padding:1px;
  background:linear-gradient(90deg,
    rgba(99,102,241,.7) 0%,rgba(167,139,250,.7) 20%,
    rgba(56,189,248,.7) 40%,rgba(74,222,128,.5) 60%,
    rgba(99,102,241,.7) 80%,rgba(167,139,250,.7) 100%);
  background-size:250% auto;
  animation:borderShimmer 4.5s linear infinite;
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}}
@keyframes borderShimmer{{to{{background-position:250% center}}}}
.msg-text{{font-size:16.5px;line-height:1.62;color:rgba(255,255,255,.9)}}
.user-bubble{{
  margin-top:11px;padding:9px 14px;
  background:rgba(99,102,241,.14);
  border-left:3px solid #818cf8;border-radius:0 11px 11px 0;
  font-size:13.5px;color:rgba(255,255,255,.78);
  animation:bubbleIn .4s ease both}}
@keyframes bubbleIn{{
  from{{opacity:0;transform:translateX(-10px)}}
  to  {{opacity:1;transform:translateX(0)}}
}}
.ulabel{{font-weight:700;color:#a5b4fc}}

/* ═══════════════════════════════════════════
   GRILLE BOUTONS
═══════════════════════════════════════════ */
.btn-grid{{display:flex;flex-direction:column;flex:1;min-height:0;gap:9px}}
.btn-row{{
  display:grid;grid-template-columns:repeat(3,1fr);
  gap:9px;flex:1;min-height:0}}

/* ═══════════════════════════════════════════
   CARTES ACTION
═══════════════════════════════════════════ */
.acard{{
  position:relative;overflow:hidden;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:5px;
  border-radius:20px;padding:14px 8px;
  cursor:pointer;
  transition:transform .15s ease,box-shadow .15s ease;
  animation:cardIn .55s ease both}}
.acard:nth-child(1){{animation-delay:.35s}}
.acard:nth-child(2){{animation-delay:.45s}}
.acard:nth-child(3){{animation-delay:.55s}}
@keyframes cardIn{{
  from{{opacity:0;transform:translateY(22px) scale(.93)}}
  to  {{opacity:1;transform:translateY(0)  scale(1)}}
}}
.acard:active{{transform:scale(.91)!important;transition:transform .07s ease}}

/* Ripple */
.ripple{{
  position:absolute;border-radius:50%;
  background:rgba(255,255,255,.28);
  transform:scale(0);
  animation:rippleA .65s ease-out forwards;pointer-events:none}}
@keyframes rippleA{{to{{transform:scale(4.5);opacity:0}}}}

.abtn{{
  display:flex;flex-direction:column;align-items:center;gap:7px;
  border:none;background:transparent;
  color:#fff;font-size:13.5px;font-weight:700;
  cursor:pointer;width:100%;letter-spacing:.2px}}
.abtn:disabled{{opacity:.6;cursor:not-allowed}}
.bicon{{
  font-size:31px;line-height:1;display:block;
  filter:drop-shadow(0 3px 10px rgba(0,0,0,.45));
  transition:transform .2s ease}}
.acard:active .bicon{{transform:scale(.82)}}
.ahint{{font-size:9.5px;color:rgba(255,255,255,.45);text-align:center}}

/* Couleurs cartes */
#callCard{{
  background:linear-gradient(148deg,rgba(37,99,235,.52),rgba(29,78,216,.32));
  border:1px solid rgba(96,165,250,.32);
  box-shadow:0 8px 28px rgba(37,99,235,.3),inset 0 1px 0 rgba(255,255,255,.09)}}
#callCard .abtn{{color:#93c5fd}}
#callCard .ahint{{color:rgba(147,197,253,.55)}}

#qrCard{{
  background:linear-gradient(148deg,rgba(124,58,237,.52),rgba(109,40,217,.32));
  border:1px solid rgba(167,139,250,.32);
  box-shadow:0 8px 28px rgba(124,58,237,.3),inset 0 1px 0 rgba(255,255,255,.09)}}
#qrCard .abtn{{color:#c4b5fd}}
#qrCard .ahint{{color:rgba(196,181,253,.55)}}

#chatCard{{
  background:linear-gradient(148deg,rgba(217,119,6,.52),rgba(180,83,9,.32));
  border:1px solid rgba(251,191,36,.32);
  box-shadow:0 8px 28px rgba(217,119,6,.3),inset 0 1px 0 rgba(255,255,255,.09)}}
#chatCard .abtn{{color:#fde68a}}
#chatCard .ahint{{color:rgba(253,230,138,.55)}}

/* ═══════════════════════════════════════════
   BOUTON MICRO
═══════════════════════════════════════════ */
.mic-card{{
  background:linear-gradient(148deg,rgba(22,163,74,.42),rgba(20,83,45,.28));
  border:1px solid rgba(74,222,128,.28);
  border-radius:20px;overflow:hidden;
  display:flex;align-items:center;gap:14px;
  padding:13px 18px;flex-shrink:0;
  box-shadow:0 8px 28px rgba(22,163,74,.22);
  animation:cardIn .55s .28s ease both}}
.mic-btn{{
  display:flex;align-items:center;gap:9px;
  background:linear-gradient(135deg,#22c55e,#15803d);
  border:none;border-radius:50px;
  padding:12px 22px;color:#fff;
  font-size:16px;font-weight:800;cursor:pointer;
  box-shadow:0 5px 18px rgba(22,163,74,.5);
  transition:transform .12s,box-shadow .12s;white-space:nowrap;flex-shrink:0}}
.mic-btn:active{{transform:scale(.94)}}
.mic-btn.mic-active{{
  background:linear-gradient(135deg,#ef4444,#b91c1c);
  box-shadow:0 5px 24px rgba(239,68,68,.55);
  animation:micGlow 1.1s ease-in-out infinite}}
@keyframes micGlow{{
  0%,100%{{box-shadow:0 5px 20px rgba(239,68,68,.5)}}
  50%    {{box-shadow:0 5px 44px rgba(239,68,68,.9),0 0 0 10px rgba(239,68,68,.1)}}
}}
.mic-btn .bicon{{font-size:21px}}
.mic-info{{flex:1;min-width:0}}
#micHint{{font-size:11.5px;color:rgba(134,239,172,.8);margin-bottom:4px}}

/* Barres d'onde (affichées pendant l'enregistrement) */
.wave-bars{{display:none;align-items:flex-end;gap:3px;height:26px}}
.wave-bars.active{{display:flex}}
.wbar{{
  width:4px;border-radius:3px;
  background:linear-gradient(to top,#4ade80,#86efac);
  animation:wBar .7s ease-in-out infinite alternate}}
.wbar:nth-child(1){{height:7px; animation-delay:.00s}}
.wbar:nth-child(2){{height:14px;animation-delay:.10s}}
.wbar:nth-child(3){{height:22px;animation-delay:.18s}}
.wbar:nth-child(4){{height:10px;animation-delay:.25s}}
.wbar:nth-child(5){{height:18px;animation-delay:.08s}}
.wbar:nth-child(6){{height:26px;animation-delay:.32s}}
.wbar:nth-child(7){{height:14px;animation-delay:.15s}}
@keyframes wBar{{from{{transform:scaleY(.25)}}to{{transform:scaleY(1)}}}}

/* ═══════════════════════════════════════════
   OVERLAY QR CHAT  (direct child of body)
═══════════════════════════════════════════ */
.qr-overlay{{
  display:none;
  position:fixed;top:0;left:0;right:0;bottom:0;
  z-index:9999;
  background:rgba(4,4,15,.96);backdrop-filter:blur(18px);
  -webkit-backdrop-filter:blur(18px);
  flex-direction:column;align-items:center;justify-content:center;padding:24px}}
.qr-box{{
  background:rgba(255,255,255,.07);
  border:1px solid rgba(255,255,255,.14);border-radius:28px;
  padding:30px 26px;max-width:310px;width:100%;text-align:center;
  box-shadow:0 20px 60px rgba(0,0,0,.55);
  animation:qbIn .35s ease both}}
@keyframes qbIn{{
  from{{opacity:0;transform:scale(.88) translateY(18px)}}
  to  {{opacity:1;transform:scale(1)   translateY(0)}}
}}
.qr-title{{font-size:18px;font-weight:700;color:#e0e7ff;margin-bottom:22px}}
.qr-img-wrap{{
  background:#fff;border-radius:16px;padding:15px;
  display:inline-block;margin-bottom:22px;
  box-shadow:0 8px 32px rgba(0,0,0,.4)}}
.qr-img-wrap img{{max-width:190px;height:auto;display:block;border-radius:8px}}
.close-btn{{
  background:rgba(99,102,241,.2);
  border:1px solid rgba(99,102,241,.4);
  border-radius:50px;padding:12px 34px;
  color:#a5b4fc;font-size:15.5px;font-weight:600;cursor:pointer;
  transition:background .15s}}
.close-btn:active{{background:rgba(99,102,241,.38)}}
</style>
</head>
<body>

<canvas id="bgCanvas"></canvas>
<div class="aurora">
  <div class="aurora-blob ab1"></div>
  <div class="aurora-blob ab2"></div>
  <div class="aurora-blob ab3"></div>
  <div class="aurora-blob ab4"></div>
</div>

<div class="wrap">

  <!-- Header -->
  <div class="hdr">
    <div class="av-wrap">
      <div class="av-ring"></div>
      <div class="av-inner">&#129302;</div>
    </div>
    <div class="hdr-info">
      <div class="hdr-name">{title}</div>
      <div class="hdr-sub">Votre assistant digital</div>
    </div>
    <div class="clock">
      <div class="clk-time" id="clkTime">--:--</div>
      <div class="clk-date" id="clkDate">&nbsp;</div>
    </div>
  </div>

  <!-- Badge statut -->
  {status_html}

  <!-- Message -->
  <div class="msg-card">
    <div class="msg-text">{message}</div>
    {subtitle_html}
  </div>

  <!-- Boutons -->
  <div class="btn-grid">
    {mic_html}
    <div class="btn-row">
      {call_slot}
      {qr_slot}
      {chat_slot}
    </div>
  </div>

</div>

<!-- Overlay QR (HORS du wrap pour éviter les problèmes de position:fixed sur Android) -->
{qr_overlay_slot}

{scripts_extra}
{mic_script}

<script>
/* ── Horloge ── */
(function tick(){{
  var n=new Date();
  var el=document.getElementById('clkTime');
  var ed=document.getElementById('clkDate');
  if(el)el.textContent=
    String(n.getHours()).padStart(2,'0')+':'+
    String(n.getMinutes()).padStart(2,'0')+':'+
    String(n.getSeconds()).padStart(2,'0');
  if(ed){{
    var D=['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
    var M=['Jan','Fev','Mar','Avr','Mai','Jun','Jul','Aou','Sep','Oct','Nov','Dec'];
    ed.textContent=D[n.getDay()]+' '+n.getDate()+' '+M[n.getMonth()];
  }}
  setTimeout(tick,1000);
}})();

/* ── Particules constellation ── */
(function(){{
  var c=document.getElementById('bgCanvas');
  if(!c)return;
  var cx=c.getContext('2d');
  var W=0,H=0,P=[];
  function resize(){{W=c.width=innerWidth;H=c.height=innerHeight;}}
  resize();
  window.addEventListener('resize',resize);
  function Pt(){{
    this.x=Math.random()*W; this.y=Math.random()*H;
    this.vx=(Math.random()-.5)*.28; this.vy=(Math.random()-.5)*.28;
    this.r=Math.random()*1.4+.4;
  }}
  for(var i=0;i<60;i++)P.push(new Pt());
  function frame(){{
    cx.clearRect(0,0,W,H);
    for(var i=0;i<P.length;i++){{
      var p=P[i];
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;
      if(p.y<0||p.y>H)p.vy*=-1;
      cx.beginPath();cx.arc(p.x,p.y,p.r,0,Math.PI*2);
      cx.fillStyle='rgba(165,180,252,.55)';cx.fill();
      for(var j=i+1;j<P.length;j++){{
        var q=P[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<130){{
          cx.beginPath();cx.moveTo(p.x,p.y);cx.lineTo(q.x,q.y);
          cx.strokeStyle='rgba(165,180,252,'+(1-d/130)*.12+')';
          cx.lineWidth=.6;cx.stroke();
        }}
      }}
    }}
    requestAnimationFrame(frame);
  }}
  frame();
}})();

/* ── Ripple au toucher ── */
(function(){{
  function addRipple(card,x,y){{
    var r=document.createElement('span');
    r.className='ripple';
    var rect=card.getBoundingClientRect();
    var s=Math.max(rect.width,rect.height)*2.2;
    r.style.cssText='width:'+s+'px;height:'+s+'px;left:'+(x-rect.left-s/2)+'px;top:'+(y-rect.top-s/2)+'px';
    card.appendChild(r);
    r.addEventListener('animationend',function(){{r.remove();}});
  }}
  document.querySelectorAll('.acard,.mic-card').forEach(function(card){{
    card.addEventListener('click',function(e){{addRipple(card,e.clientX,e.clientY);}});
    card.addEventListener('touchstart',function(e){{
      if(e.touches.length)addRipple(card,e.touches[0].clientX,e.touches[0].clientY);
    }},{{passive:true}});
  }});
}})();
</script>
</body>
</html>"""


def create_tablet_html(
    title,
    message,
    subtitle="",
    status="",
    show_mic_button=False,
    mic_active=False,
    api_url=None,
    show_call_button=None,
    show_qr_button=False,
    robot_ip=None,
):
    """Crée le HTML pour la tablette avec design premium animé.
    show_call_button: True/False pour forcer, None = utiliser SHOW_TABLET_CALL_BUTTON (config/env).
    """
    if show_call_button is None:
        show_call_button = SHOW_TABLET_CALL_BUTTON

    title    = force_utf8(title)
    message  = force_utf8(message)
    subtitle = force_utf8(subtitle)
    status   = force_utf8(status)

    if api_url is None:
        if robot_ip:
            local_ip = get_local_ip_for_robot(robot_ip)
            api_url = "http://{}:5000".format(local_ip)
        else:
            api_url = API_CONFIG["base_url"]

    title_s   = transliterate_to_ascii(escape_html(title))   if title   else "Pepper"
    message_s = transliterate_to_ascii(escape_html(message)) if message else ""
    sub_s     = transliterate_to_ascii(escape_html(subtitle)) if subtitle else ""
    status_s  = transliterate_to_ascii(escape_html(status))   if status   else ""

    # ── Status badge ─────────────────────────────────────────────────────────
    status_html = u""
    if status_s:
        status_html = u"""<div class="status-badge"><span class="sdot"></span><span>{}</span></div>""".format(status_s)

    # ── Subtitle bubble ───────────────────────────────────────────────────────
    subtitle_html = u""
    if sub_s:
        subtitle_html = u"""<div class="user-bubble"><span class="ulabel">Vous :</span> {}</div>""".format(sub_s)

    # ── Bouton Micro ──────────────────────────────────────────────────────────
    mic_html = u""
    mic_script = u""
    if show_mic_button:
        mic_js = u"true" if mic_active else u"false"
        hint   = u"Parlez..." if mic_active else u"Appuyez pour parler"
        acls   = u"mic-active" if mic_active else u""
        mic_html = u"""
<div class="mic-card" id="micCard">
  <button id="micBtn" class="mic-btn {acls}" onclick="toggleMic()">
    <span id="micIcon" class="bicon">&#127908;</span>
    <span id="micLbl">MIC</span>
  </button>
  <div class="mic-info">
    <div id="micHint">{hint}</div>
    <div class="wave-bars" id="waveBars">
      <div class="wbar"></div><div class="wbar"></div><div class="wbar"></div>
      <div class="wbar"></div><div class="wbar"></div><div class="wbar"></div>
      <div class="wbar"></div>
    </div>
  </div>
</div>""".format(acls=acls, hint=hint)

        mic_script = u"""
<script>
var _isRec={mic_js};
var _api='{api}';
function _xpost(url,cb){{
  var r=new XMLHttpRequest();r.open('POST',url,true);
  r.setRequestHeader('Content-Type','application/json');
  r.onreadystatechange=function(){{if(r.readyState===4)cb(r.status>=200&&r.status<300);}};
  r.onerror=function(){{cb(false);}};r.send();
}}
function toggleMic(){{
  var btn=document.getElementById('micBtn');
  var hint=document.getElementById('micHint');
  var icon=document.getElementById('micIcon');
  var lbl=document.getElementById('micLbl');
  var bars=document.getElementById('waveBars');
  if(!_isRec){{
    hint.textContent='Connexion...';
    _xpost(_api+'/record/start',function(ok){{
      if(ok){{
        _isRec=true;
        btn.classList.add('mic-active');
        icon.innerHTML='&#9209;';lbl.textContent='STOP';
        hint.textContent='Parlez — arret auto 2 sec silence';
        if(bars)bars.classList.add('active');
      }}else{{hint.textContent='Erreur connexion';}}
    }});
  }}else{{
    hint.textContent='Arret...';
    _xpost(_api+'/record/stop',function(ok){{
      if(ok){{
        _isRec=false;
        btn.classList.remove('mic-active');
        icon.innerHTML='&#127908;';lbl.textContent='MIC';
        hint.textContent='Enregistrement termine';
        if(bars)bars.classList.remove('active');
      }}else{{hint.textContent='Erreur';}}
    }});
  }}
}}
</script>""".format(mic_js=mic_js, api=api_url)

    # ── Bouton Appel ──────────────────────────────────────────────────────────
    call_html = u""
    call_script = u""
    if show_call_button and api_url:
        call_url = api_url.rstrip("/") + "/tablet/call/start"
        call_html = u"""
<div class="acard" id="callCard">
  <button class="abtn" onclick="doCall(this)">
    <span class="bicon">&#128222;</span>
    <span>Appel</span>
  </button>
  <p class="ahint">Agent en direct</p>
</div>"""
        call_script = u"""
<script>
var _callUrl='{u}';
function doCall(btn){{
  btn.disabled=true;
  btn.innerHTML='<span class="bicon">&#8987;</span><span>...</span>';
  var r=new XMLHttpRequest();r.open('POST',_callUrl,true);
  r.setRequestHeader('Content-Type','application/json');
  r.onreadystatechange=function(){{
    if(r.readyState===4){{btn.disabled=false;btn.innerHTML='<span class="bicon">&#128222;</span><span>Appel</span>';}}
  }};r.send();
}}
</script>""".format(u=call_url)

    # ── Bouton Scan QR ────────────────────────────────────────────────────────
    qr_html = u""
    qr_script = u""
    if show_qr_button and api_url:
        scan_url = api_url.rstrip("/") + "/tablet/scan_qr/start"
        qr_html = u"""
<div class="acard" id="qrCard">
  <button class="abtn" onclick="doScan(this)">
    <span class="bicon">&#128247;</span>
    <span>Scan QR</span>
  </button>
  <p class="ahint">Ma reservation</p>
</div>"""
        qr_script = u"""
<script>
var _scanUrl='{u}';
function doScan(btn){{
  btn.disabled=true;
  btn.innerHTML='<span class="bicon">&#128269;</span><span>Scan...</span>';
  var r=new XMLHttpRequest();r.open('POST',_scanUrl,true);
  r.setRequestHeader('Content-Type','application/json');
  r.onreadystatechange=function(){{
    if(r.readyState===4){{setTimeout(function(){{
      btn.disabled=false;
      btn.innerHTML='<span class="bicon">&#128247;</span><span>Scan QR</span>';
    }},2200);}}
  }};r.send();
}}
</script>""".format(u=scan_url)

    # ── Bouton Chat (sans l'overlay, il est sorti du wrap) ───────────────────
    chat_html = u""
    qr_overlay_html = u""  # sera injecté HORS du .wrap
    chat_script = u""
    if api_url:
        qr_img = "{}/chat/qrcode".format(api_url.rstrip('/'))
        # Seulement le bouton dans la grille
        chat_html = u"""
<div class="acard" id="chatCard">
  <button class="abtn" id="chatBtn" onclick="toggleQr()">
    <span class="bicon">&#128172;</span>
    <span>Chat</span>
  </button>
  <p class="ahint">QR code chat</p>
</div>"""
        # L'overlay est un enfant direct de <body> (position:fixed fiable)
        qr_overlay_html = u"""
<div id="qrOverlay" class="qr-overlay">
  <div class="qr-box">
    <p class="qr-title">Scannez pour acceder au chat</p>
    <div class="qr-img-wrap"><img src="{img}" alt="QR Code"></div>
    <button class="close-btn" onclick="toggleQr()">&#8592; Retour</button>
  </div>
</div>""".format(img=qr_img)
        chat_script = u"""
<script>
function toggleQr(){{
  var ov=document.getElementById('qrOverlay');
  var btn=document.getElementById('chatBtn');
  var open=ov.style.display==='flex';
  ov.style.display=open?'none':'flex';
  if(btn)btn.style.display=open?'flex':'none';
}}
</script>"""

    scripts_extra = call_script + qr_script + chat_script

    return _HTML.format(
        title=title_s,
        message=message_s,
        status_html=status_html,
        subtitle_html=subtitle_html,
        mic_html=mic_html,
        call_slot=call_html,
        qr_slot=qr_html,
        chat_slot=chat_html,
        qr_overlay_slot=qr_overlay_html,
        scripts_extra=scripts_extra,
        mic_script=mic_script,
    )
