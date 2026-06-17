import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date
import textwrap
import json
import os
import re
from PIL import Image
from api_client import api_client

_BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")

def _load_mascot_data_uri() -> str:
    import base64
    _img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "mascot.jpg")
    try:
        with open(_img_path, "rb") as _f:
            return "data:image/jpeg;base64," + base64.b64encode(_f.read()).decode()
    except FileNotFoundError:
        return ""

_MASCOT_DATA_URI = _load_mascot_data_uri()

def _fix_mascot(html: str) -> str:
    """Replace expired Google AIDA signed image URLs with local alternatives."""
    # 1. Replace any img with alt="ALP Mascot" with the local mascot (must run before generic AB6AXu sweep)
    if _MASCOT_DATA_URI:
        html = re.sub(
            r'<img\b[^>]*\balt="ALP Mascot"[^>]*>',
            f'<img alt="ALP Mascot" class="w-24 h-auto drop-shadow-sm" src="{_MASCOT_DATA_URI}">',
            html
        )
    else:
        html = re.sub(
            r'<img\b[^>]*\balt="ALP Mascot"[^>]*>',
            '<span class="material-symbols-outlined" style="font-size:48px;font-variation-settings:\'FILL\' 1;color:#FF385C;">smart_toy</span>',
            html
        )
    # 2. Replace the older AP1WRLvOiaJlD5i6 signed URLs (used in homepage template)
    if _MASCOT_DATA_URI:
        html = re.sub(
            r'(<img\b[^>]*)src="[^"]*AP1WRLvOiaJlD5i6[^"]*"([^>]*>)',
            rf'\1src="{_MASCOT_DATA_URI}"\2',
            html
        )
    else:
        html = re.sub(
            r'<img\b[^>]*AP1WRLvOiaJlD5i6[^>]*>',
            '<span class="material-symbols-outlined" style="font-size:28px;font-variation-settings:\'FILL\' 1;color:#FF385C;flex-shrink:0;">smart_toy</span>',
            html
        )
    # 3. Replace remaining expired aida-public activity card images with a gradient placeholder
    html = re.sub(
        r'<img\b[^>]*lh3\.googleusercontent\.com/aida-public/AB6AXu[^>]*>',
        '<div style="width:100%;height:100%;background:linear-gradient(135deg,#FF385C18,#fbf9f8);'
        'display:flex;align-items:center;justify-content:center;">'
        '<span class="material-symbols-outlined" style="font-size:48px;color:#FF385C;opacity:0.25;'
        'font-variation-settings:\'FILL\' 1;">event</span></div>',
        html
    )
    return html

SESSION_FILE = os.path.expanduser("~/.after_work_agent_session.json")

def _save_session(user_id: int, is_onboarded: bool, token: str) -> None:
    with open(SESSION_FILE, "w") as f:
        json.dump({"user_id": user_id, "is_onboarded": is_onboarded, "token": token}, f)

def _load_session() -> dict | None:
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except Exception:
        return None

def _clear_session() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def render_html(html_str):
    cleaned = "\n".join(line.strip() for line in html_str.split("\n"))
    st.markdown(cleaned, unsafe_allow_html=True)


def _build_auth_html() -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/sign_in_afterwork_agent_updated_background/code.html")) as f:
        html = f.read()
    html = _fix_mascot(html)

    # Fix domain input: type="email" -> type="text", update id
    html = html.replace(
        'id="email" name="email" placeholder="annt7" required="" type="email"',
        'id="login-domain" placeholder="annt7" type="text"',
    )

    # Add id to login submit button and insert error paragraph before it
    html = html.replace(
        '<button class="btn-premium w-full h-14 bg-rausch text-white font-button-md text-button-md rounded-lg flex items-center justify-center gap-stack-sm hover:bg-rausch-active shadow-md hover:shadow-lg mt-stack-md" type="submit">',
        '<p id="login-error" class="text-sm text-red-600 hidden"></p>'
        '<button id="login-btn" class="btn-premium w-full h-14 bg-rausch text-white font-button-md text-button-md rounded-lg flex items-center justify-center gap-stack-sm hover:bg-rausch-active shadow-md hover:shadow-lg mt-stack-md" type="submit">',
    )

    # Wire "Register now" link
    html = html.replace(
        '<a class="text-rausch font-bold hover:underline underline-offset-4" href="#">Register now</a>',
        '<a class="text-rausch font-bold hover:underline underline-offset-4 cursor-pointer" onclick="showRegister()">Register now</a>',
    )

    # Inject register panel before <footer>
    register_panel = """
<div id="register-panel" style="display:none" class="editorial-canvas">
<div class="login-card p-stack-xl md:p-12 rounded-xl shadow-sm border border-hairline">
<div class="flex flex-col items-center mb-stack-xl text-center">
<div class="mb-stack-lg transition-transform hover:scale-105 duration-300">
<img alt="ALP Mascot" class="w-24 h-24 w-auto drop-shadow-sm" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1qf9VJDK8-cUR6PBj9u_H6Pr7_lXjm6FycC3FOzz6MHLTT9KQOeBi7_liqfQk__Gq2e5TadZKwr2dfKIaN12OzFYG6Qp8VkSHnx3Jzs-pqaaSgB6bTSthAJ0N9EgC6mtzFgKAvhCfmU0YNG2nKnBVRmDLJyWugl7xk-e7nCQYYqjywL3QiqdQzv8-Dde5OTLvMAGfsxkCrv6eMt8IkWrVc1yjTnH0h70Kzc2VeY8jGxK6QqQb4edEEao3b6OhLmi42yTSkUQxn2I">
</div>
<h1 class="font-display-xl text-display-xl-mobile md:text-display-xl text-ink mb-stack-xs">Welcome to ALP</h1>
<p class="font-body-md text-secondary max-w-[300px]">Connect with colleagues, discover activities, and build your community.</p>
</div>
<form class="space-y-stack-lg" id="registerForm">
<div class="space-y-stack-xs">
<label class="font-caption text-caption text-secondary px-1" for="reg-domain">VNG Domain</label>
<input class="input-premium w-full h-14 px-4 rounded-lg border border-hairline focus:ring-0 focus:border-ink outline-none text-ink placeholder:text-secondary-fixed-dim" id="reg-domain" placeholder="annt7" type="text">
</div>
<div class="space-y-stack-xs">
<label class="font-caption text-caption text-secondary px-1" for="reg-password">Password</label>
<div class="relative">
<input class="input-premium w-full h-14 px-4 rounded-lg border border-hairline focus:ring-0 focus:border-ink outline-none text-ink placeholder:text-secondary-fixed-dim" id="reg-password" placeholder="••••••••" type="password">
<button class="absolute right-4 top-1/2 -translate-y-1/2 text-secondary hover:text-ink" onclick="toggleRegPass()" type="button">
<span class="material-symbols-outlined text-[20px]" id="reg-pass-icon">visibility</span>
</button>
</div>
</div>
<p id="register-error" class="text-sm text-red-600 hidden"></p>
<button id="register-btn" class="btn-premium w-full h-14 bg-rausch text-white font-button-md text-button-md rounded-lg flex items-center justify-center gap-stack-sm hover:bg-rausch-active shadow-md hover:shadow-lg mt-stack-md" type="submit">
Create Account
</button>
</form>
<p class="mt-stack-xl text-center font-body-sm text-secondary">
Already have an account?
<a class="text-rausch font-bold hover:underline underline-offset-4 cursor-pointer" onclick="showLogin()">Sign in</a>
</p>
</div>
</div>
"""
    html = html.replace('<main class="editorial-canvas">', '<main class="editorial-canvas" id="login-main" style="display:none">')
    _restore_overlay = (
        '<style>'
        '@keyframes _alp_dot{0%,80%,100%{transform:scale(0.6);opacity:0.4}40%{transform:scale(1);opacity:1}}'
        '#auto-restore-overlay .d1{animation:_alp_dot 1.2s ease-in-out infinite}'
        '#auto-restore-overlay .d2{animation:_alp_dot 1.2s ease-in-out 0.2s infinite}'
        '#auto-restore-overlay .d3{animation:_alp_dot 1.2s ease-in-out 0.4s infinite}'
        '@keyframes _alp_in{from{opacity:0;transform:scale(0.92)}to{opacity:1;transform:scale(1)}}'
        '#auto-restore-overlay .card{animation:_alp_in 0.35s cubic-bezier(0.34,1.56,0.64,1) forwards}'
        '</style>'
        '<div id="auto-restore-overlay" style="display:none;position:fixed;inset:0;'
        'background:linear-gradient(160deg,#FFF5F0 0%,#FFF0F5 100%);'
        'align-items:center;justify-content:center;z-index:100;flex-direction:column;gap:0">'
        '<div class="card" style="display:flex;flex-direction:column;align-items:center;gap:20px;'
        'background:white;border-radius:24px;padding:40px 48px;'
        'box-shadow:0 8px 40px rgba(255,56,92,0.12),0 2px 12px rgba(0,0,0,0.06);">'
        '<div style="width:72px;height:72px;border-radius:50%;overflow:hidden;'
        'box-shadow:0 4px 16px rgba(255,56,92,0.2)">'
        f'<img src="{_MASCOT_DATA_URI}" style="width:100%;height:100%;object-fit:cover"></div>'
        '<div style="text-align:center">'
        '<p style="font-family:\'Inter\',sans-serif;font-size:17px;font-weight:600;color:#222;margin:0 0 4px">ALP</p>'
        '<p style="font-family:\'Inter\',sans-serif;font-size:13px;color:#888;margin:0">Finding something great for you...</p>'
        '</div>'
        '<div style="display:flex;gap:7px;align-items:center">'
        '<span class="d1" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>'
        '<span class="d2" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>'
        '<span class="d3" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>'
        '</div>'
        '</div>'
        '</div>'
    )
    html = html.replace("<footer", register_panel + "\n" + _restore_overlay + "\n<footer")

    # Replace mock script with real API calls + Streamlit component protocol
    new_script = """<script>
const BACKEND = '{_BACKEND_URL}';
const AW_SESSION_KEY = 'aw_auth_session';

// Minimal Streamlit component protocol
var Streamlit = {
  setComponentReady: function() {
    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');
  },
  setComponentValue: function(value) {
    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:value},'*');
  },
  setFrameHeight: function(h) {
    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*');
  }
};
Streamlit.setComponentReady();
Streamlit.setFrameHeight(820);
(function(){try{var pd=window.parent.document;if(!pd.getElementById('_alp_chrome_css')){var s=pd.createElement('style');s.id='_alp_chrome_css';s.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{display:none!important}.main .block-container{padding:0!important;max-width:100%!important}[data-testid="stApp"],.stApp{background:#FFF5F0!important}';pd.head.appendChild(s);}}catch(e){}})();

// Synchronous check: hide login form immediately if saved session exists
(function() {
  try {
    var saved = JSON.parse(localStorage.getItem(AW_SESSION_KEY) || 'null');
    var main = document.getElementById('login-main');
    var overlay = document.getElementById('auto-restore-overlay');
    if (saved && saved.token) {
      if (overlay) overlay.style.display = 'flex';
      _showParentCover(); // covers parent before splash disappears on next rerender
    } else {
      if (main) main.style.display = '';  // show login form
    }
  } catch(e) {
    var main = document.getElementById('login-main');
    if (main) main.style.display = '';
  }
})();

// Async validation of saved token
(async function autoRestore() {
  function showLogin() {
    var main = document.getElementById('login-main');
    var overlay = document.getElementById('auto-restore-overlay');
    if (main) main.style.display = '';
    if (overlay) overlay.style.display = 'none';
  }
  try {
    var saved = JSON.parse(localStorage.getItem(AW_SESSION_KEY) || 'null');
    if (!saved || !saved.token) return;
    var r = await fetch(BACKEND + '/api/auth/me?token=' + encodeURIComponent(saved.token));
    var data = await r.json();
    if (data.success) {
      _showParentCover();
      Streamlit.setComponentValue({token: data.token, uid: data.user_id, onboarded: data.is_onboarded});
    } else {
      localStorage.removeItem(AW_SESSION_KEY);
      showLogin();
    }
  } catch(e) { showLogin(); }
})();

function showRegister() {
  document.querySelector('main').style.display = 'none';
  document.getElementById('register-panel').style.display = 'flex';
  document.getElementById('reg-domain').focus();
}
function showLogin() {
  document.getElementById('register-panel').style.display = 'none';
  document.querySelector('main').style.display = 'flex';
  document.getElementById('login-domain').focus();
}

// Inject a full-page cover into the parent document immediately when login starts.
// This covers the page during Python processing (all API calls, HTML build) so the
// user never sees a flash of the auth form or blank state between login and main view.
function _showParentCover() {
  try {
    var pd = window.parent.document;
    var cov = pd.getElementById('_alp_tr_cover');
    if (!cov) {
      if (!pd.getElementById('_alp_tc_anim')) {
        var ka = pd.createElement('style');
        ka.id = '_alp_tc_anim';
        ka.textContent = '@keyframes _alp_tc{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}';
        pd.head.appendChild(ka);
      }
      // Grab mascot data-URI from the auth overlay already in DOM
      var _mEl = document.querySelector('#auto-restore-overlay img');
      var _mSrc = _mEl ? _mEl.src : '';
      var _mascotHtml = _mSrc
        ? '<div style="width:72px;height:72px;border-radius:50%;overflow:hidden;box-shadow:0 4px 16px rgba(255,56,92,.2)"><img src="' + _mSrc + '" style="width:100%;height:100%;object-fit:cover"></div>'
        : '';
      cov = pd.createElement('div');
      cov.id = '_alp_tr_cover';
      cov.style.cssText = 'position:fixed;inset:0;background:linear-gradient(160deg,#FFF5F0 0%,#FFF0F5 100%);z-index:99999;display:flex;align-items:center;justify-content:center;';
      cov.innerHTML = '<div style="background:white;border-radius:24px;padding:40px 48px;display:flex;flex-direction:column;align-items:center;gap:20px;text-align:center;box-shadow:0 8px 40px rgba(255,56,92,.12),0 2px 12px rgba(0,0,0,.06)">' + _mascotHtml + '<div><p style="font-family:Inter,sans-serif;font-size:17px;font-weight:600;color:#222;margin:0 0 4px">ALP</p><p style="font-family:Inter,sans-serif;font-size:13px;color:#888;margin:0">Finding something great for you...</p></div><div style="display:flex;gap:7px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C;animation:_alp_tc 1.2s ease-in-out 0s infinite both"></span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C;animation:_alp_tc 1.2s ease-in-out .2s infinite both"></span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C;animation:_alp_tc 1.2s ease-in-out .4s infinite both"></span></div></div>';
      pd.body.appendChild(cov);
    } else {
      cov.style.display = 'flex';
    }
  } catch(e) {}
}

var _pwdToggle = document.querySelector('#loginForm button[type="button"]');
if (_pwdToggle) _pwdToggle.addEventListener('click', () => {
  const inp = document.getElementById('password');
  const ic = inp.closest('.relative').querySelector('.material-symbols-outlined');
  inp.type = inp.type === 'password' ? 'text' : 'password';
  if (ic) ic.textContent = inp.type === 'password' ? 'visibility' : 'visibility_off';
});

function toggleRegPass() {
  const inp = document.getElementById('reg-password');
  const ic = document.getElementById('reg-pass-icon');
  inp.type = inp.type === 'password' ? 'text' : 'password';
  ic.textContent = inp.type === 'password' ? 'visibility' : 'visibility_off';
}

var _loginForm = document.getElementById('loginForm');
if (_loginForm) _loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const domain = document.getElementById('login-domain').value.trim();
  const password = document.getElementById('password').value;
  const errEl = document.getElementById('login-error');
  const btn = document.getElementById('login-btn');
  const orig = btn.innerHTML;
  errEl.classList.add('hidden');
  if (!domain || !password) { errEl.textContent = 'Please fill in both fields.'; errEl.classList.remove('hidden'); return; }
  btn.disabled = true;
  btn.innerHTML = '<div class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>&nbsp;Signing in...';
  try {
    const r = await fetch(BACKEND + '/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain, password})});
    const data = await r.json();
    if (data.success) {
      btn.innerHTML = '<span class="material-symbols-outlined">check_circle</span>&nbsp;Welcome back!';
      localStorage.setItem(AW_SESSION_KEY, JSON.stringify({token:data.token, uid:data.user_id, onboarded:data.is_onboarded}));
      _showParentCover();
      Streamlit.setComponentValue({token:data.token, uid:data.user_id, onboarded:data.is_onboarded});
    } else {
      errEl.textContent = data.message || 'Invalid credentials'; errEl.classList.remove('hidden');
      btn.disabled = false; btn.innerHTML = orig;
    }
  } catch { errEl.textContent = 'Connection error. Please try again.'; errEl.classList.remove('hidden'); btn.disabled = false; btn.innerHTML = orig; }
});

var _regForm = document.getElementById('registerForm');
if (_regForm) _regForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const domain = document.getElementById('reg-domain').value.trim();
  const password = document.getElementById('reg-password').value;
  const errEl = document.getElementById('register-error');
  const btn = document.getElementById('register-btn');
  const orig = btn.innerHTML;
  errEl.classList.add('hidden');
  if (!domain || !password) { errEl.textContent = 'Please fill in both fields.'; errEl.classList.remove('hidden'); return; }
  btn.disabled = true;
  btn.innerHTML = '<div class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>&nbsp;Creating account...';
  try {
    const r = await fetch(BACKEND + '/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain, password})});
    const data = await r.json();
    if (data.success) {
      btn.innerHTML = '<span class="material-symbols-outlined">check_circle</span>&nbsp;Welcome aboard!';
      localStorage.setItem(AW_SESSION_KEY, JSON.stringify({token:data.token, uid:data.user_id, onboarded:data.is_onboarded}));
      _showParentCover();
      Streamlit.setComponentValue({token:data.token, uid:data.user_id, onboarded:data.is_onboarded});
    } else {
      errEl.textContent = data.message || 'Error creating account'; errEl.classList.remove('hidden');
      btn.disabled = false; btn.innerHTML = orig;
    }
  } catch { errEl.textContent = 'Connection error. Please try again.'; errEl.classList.remove('hidden'); btn.disabled = false; btn.innerHTML = orig; }
});
</script>"""

    new_script = new_script.replace('{_BACKEND_URL}', _BACKEND_URL)
    html = re.sub(r"<script>.*?</script>\s*(?=</body>)", new_script + "\n", html, flags=re.DOTALL)
    return html


def _build_onboarding1_html() -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/onboarding_step_1_your_info_updated/code.html")) as f:
        html = f.read()
    html = _fix_mascot(html)
    new_script = '''<script>
var Streamlit={
  setComponentReady:function(){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');},
  setComponentValue:function(v){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:v},'*');},
  setFrameHeight:function(h){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*');}
};
Streamlit.setComponentReady();
(function(){try{var pd=window.parent.document;if(!pd.getElementById('_alp_chrome_css')){var s=pd.createElement('style');s.id='_alp_chrome_css';s.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{display:none!important}.main .block-container{padding:0!important;max-width:100%!important}[data-testid="stApp"],.stApp{background:#FFF5F0!important}';pd.head.appendChild(s);}var _c=pd.getElementById('_alp_tr_cover');if(_c)_c.parentNode.removeChild(_c);}catch(e){}})();
window.addEventListener('load',function(){Streamlit.setFrameHeight(document.documentElement.scrollHeight);});
document.addEventListener('DOMContentLoaded',function(){
  var card=document.querySelector('.bg-canvas.rounded-xl');
  if(card){
    card.style.opacity='0';card.style.transform='translateY(20px)';
    card.style.transition='all 0.6s cubic-bezier(0.16,1,0.3,1)';
    setTimeout(function(){
      card.style.opacity='1';card.style.transform='translateY(0)';
      Streamlit.setFrameHeight(document.documentElement.scrollHeight);
    },100);
  }
});
var _ob1Back=document.getElementById('ob1-back-btn');
if(_ob1Back)_ob1Back.addEventListener('click',function(){
  Streamlit.setComponentValue({action:'back'});
});
var _ob1Form=document.getElementById('onboarding1Form');
if(_ob1Form)_ob1Form.addEventListener('submit',function(e){
  e.preventDefault();
  var fn=document.getElementById('ob1-full-name').value.trim();
  var errEl=document.getElementById('ob1-error');
  if(!fn){errEl.textContent='Please enter your Full Name.';errEl.classList.remove('hidden');return;}
  errEl.classList.add('hidden');
  var btn=e.target.querySelector('button[type="submit"]');
  btn.disabled=true;btn.textContent='Saving…';
  var _c1=document.querySelector('.bg-canvas.rounded-xl');
  if(_c1){_c1.style.transition='opacity 0.22s ease,transform 0.22s ease';_c1.style.opacity='0';_c1.style.transform='translateX(-28px)';}
  setTimeout(function(){
    try{var pd=window.parent.document;var _cv=pd.getElementById('_alp_tr_cover')||pd.createElement('div');_cv.id='_alp_tr_cover';_cv.style.cssText='position:fixed;inset:0;background:#FFF5F0;z-index:99999;';if(!_cv.parentNode)pd.body.appendChild(_cv);}catch(e2){}
    Streamlit.setComponentValue({
      action:'continue',
      full_name:fn,
      horoscope:document.getElementById('ob1-horoscope').value,
      business_unit:document.getElementById('ob1-bu').value,
      department:document.getElementById('ob1-dept').value.trim(),
      org_group:document.getElementById('ob1-group').value.trim(),
      squad:document.getElementById('ob1-squad').value.trim()
    });
  },230);
});
</script>'''
    html = re.sub(r"<footer.*?</footer>", "", html, flags=re.DOTALL)
    html = re.sub(r"<script>.*?</script>\s*(?=</body>)", new_script + "\n", html, flags=re.DOTALL)
    return html

def _build_onboarding2_html() -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/onboarding_step_2_interests_hobbies/code.html")) as f:
        html = f.read()
    html = _fix_mascot(html)
    html = html.replace(
        '</head>',
        '<style>.tag-active{border-color:#FF385C!important;color:#FF385C!important;background-color:#FFF5F7!important;font-weight:600;}</style></head>',
    )
    html = html.replace(
        '<button class="font-button-md text-button-md text-secondary hover:text-ink transition-colors px-6 py-3">',
        '<button id="ob2-back-btn" class="font-button-md text-button-md text-secondary hover:text-ink transition-colors px-6 py-3">',
    )
    html = html.replace(
        '<button class="bg-rausch hover:bg-rausch-active text-white font-button-md text-button-md px-10 py-4 rounded-lg transition-all transform active:scale-95 shadow-lg shadow-rausch/20 w-full md:w-auto">',
        '<p id="ob2-error" class="text-sm text-red-600 hidden w-full text-center"></p>'
        '<button id="ob2-complete-btn" class="bg-rausch hover:bg-rausch-active text-white font-button-md text-button-md px-10 py-4 rounded-lg transition-all transform active:scale-95 shadow-lg shadow-rausch/20 w-full md:w-auto">',
    )
    html = re.sub(r"<footer.*?</footer>", "", html, flags=re.DOTALL)
    new_script = '''<script>
var Streamlit={
  setComponentReady:function(){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');},
  setComponentValue:function(v){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:v},'*');},
  setFrameHeight:function(h){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*');}
};
Streamlit.setComponentReady();
(function(){try{var pd=window.parent.document;if(!pd.getElementById('_alp_chrome_css')){var s=pd.createElement('style');s.id='_alp_chrome_css';s.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{display:none!important}.main .block-container{padding:0!important;max-width:100%!important}[data-testid="stApp"],.stApp{background:#FFF5F0!important}';pd.head.appendChild(s);}var _c=pd.getElementById('_alp_tr_cover');if(_c)_c.parentNode.removeChild(_c);}catch(e){}})();
window.addEventListener('load',function(){Streamlit.setFrameHeight(document.documentElement.scrollHeight);});
document.addEventListener('DOMContentLoaded',function(){
  var card=document.querySelector('.bg-canvas.rounded-lg');
  if(card){
    card.style.opacity='0';card.style.transform='translateX(28px)';
    card.style.transition='opacity 0.35s cubic-bezier(0.16,1,0.3,1),transform 0.35s cubic-bezier(0.16,1,0.3,1)';
    setTimeout(function(){card.style.opacity='1';card.style.transform='translateX(0)';Streamlit.setFrameHeight(document.documentElement.scrollHeight);},50);
  }
});

function toggleTag(button){
  button.classList.toggle('tag-active');
  button.classList.toggle('border-hairline');
  if(button.classList.contains('tag-active')){
    button.style.transform='scale(1.05)';
    setTimeout(function(){button.style.transform='scale(1)';},150);
  }
}

var _ob2Back=document.getElementById('ob2-back-btn');
if(_ob2Back)_ob2Back.addEventListener('click',function(){
  Streamlit.setComponentValue({action:'back'});
});

var _ob2Complete=document.getElementById('ob2-complete-btn');
if(_ob2Complete)_ob2Complete.addEventListener('click',function(){
  var interests=[];
  document.querySelectorAll('.tag-active').forEach(function(btn){
    interests.push(btn.textContent.trim());
  });
  var btn=document.getElementById('ob2-complete-btn');
  btn.disabled=true;btn.textContent='Saving…';
  var _c2=document.querySelector('.bg-canvas.rounded-lg');
  if(_c2){_c2.style.transition='opacity 0.22s ease,transform 0.22s ease';_c2.style.opacity='0';_c2.style.transform='translateX(-28px)';}
  setTimeout(function(){
    try{var pd=window.parent.document;var _cv=pd.getElementById('_alp_tr_cover')||pd.createElement('div');_cv.id='_alp_tr_cover';_cv.style.cssText='position:fixed;inset:0;background:#FFF5F0;z-index:99999;';if(!_cv.parentNode)pd.body.appendChild(_cv);}catch(e2){}
    Streamlit.setComponentValue({action:'complete',interests:interests});
  },230);
});
</script>'''
    html = re.sub(r"<script>.*?</script>\s*(?=</body>)", new_script + "\n", html, flags=re.DOTALL)
    return html


def _escape_html(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


_HP_TYPE_COLORS = {
    "gym": "#FF385C", "yoga": "#558B2F", "zumba": "#C2185B", "boxing": "#B71C1C",
    "swimming": "#0288D1", "football": "#FF6B35", "pickleball": "#7742AA",
    "badminton": "#7742AA", "running": "#1A7A4A", "taekwondo": "#5D4037",
    "board games": "#B7691B", "movies": "#455A64", "dining": "#E65100",
    "esports": "#1565C0", "coffee chat": "#6D4C41", "karaoke": "#AD1457",
    "picnics": "#558B2F", "concerts": "#6A1B9A", "ai": "#1D6FA4",
    "product": "#2E7D32", "english": "#0277BD", "book club": "#4527A0",
    "knowledge-sharing": "#00695C",
}
_HP_EMOJI_MAP = {
    "gym": "🏋️", "yoga": "🧘", "zumba": "💃", "boxing": "🥊", "swimming": "🏊",
    "football": "⚽", "pickleball": "🏓", "badminton": "🏸", "running": "🏃",
    "taekwondo": "🥋", "board games": "🎲", "movies": "🎬", "dining": "🍽️",
    "esports": "🎮", "coffee chat": "☕", "karaoke": "🎤", "picnics": "🧺",
    "concerts": "🎵", "ai": "🤖", "product": "📦", "english": "📚",
    "book club": "📖", "knowledge-sharing": "💡",
    "book": "📚", "reading": "📚", "workshop": "📚", "hiking": "🥾",
}


def _build_chat_messages_html(chat_history: list) -> str:
    if not chat_history:
        return ""
    msgs = []
    for msg in chat_history:
        content = _escape_html(msg.get("content", ""))
        if msg["role"] == "assistant":
            msgs.append(
                f'<div class="flex items-start gap-3 mb-4">'
                f'<div class="w-8 h-8 rounded-full flex-shrink-0 overflow-hidden"><img src="{_MASCOT_DATA_URI}" style="width:100%;height:100%;object-fit:cover;"></div>'
                f'<div class="bg-surface-soft border border-hairline rounded-xl rounded-tl-none p-3" style="max-width:80%">'
                f'<p class="font-body-sm text-body-sm text-ink" style="white-space:pre-wrap;margin:0">{content}</p>'
                f"</div></div>"
            )
        else:
            msgs.append(
                f'<div class="flex items-start gap-3 mb-4 flex-row-reverse">'
                f'<div class="w-8 h-8 bg-rausch rounded-full flex items-center justify-center text-white flex-shrink-0" style="font-size:16px;">👤</div>'
                f'<div class="rounded-xl rounded-tr-none p-3" style="max-width:80%;background:rgba(255,56,92,0.1)">'
                f'<p class="font-body-sm text-body-sm text-ink" style="white-space:pre-wrap;margin:0">{content}</p>'
                f"</div></div>"
            )
    return f'<div id="hp-chat-messages" class="w-full pt-4 pb-4">{"".join(msgs)}</div>'


_DIFF_BADGE_CFG = {
    "Beginner":     ("#E8F5E9", "#2E7D32", "signal_cellular_1_bar"),
    "Intermediate": ("#FFF8E1", "#F57F17", "signal_cellular_2_bar"),
    "Advanced":     ("#FCE4EC", "#C62828", "signal_cellular_4_bar"),
    "All Levels":   ("#F3E5F5", "#6A1B9A", "signal_cellular_alt"),
}

def _difficulty_badge(difficulty: str, absolute: bool = True) -> str:
    cfg = _DIFF_BADGE_CFG.get(difficulty)
    if not cfg:
        return ""
    bg, tc, icon = cfg
    pos = 'position:absolute;top:12px;left:12px;' if absolute else ''
    return (
        f'<div style="{pos}padding:3px 10px;border-radius:999px;display:inline-flex;align-items:center;gap:4px;background:{bg}">'
        f'<span class="material-symbols-outlined" style="font-size:13px;color:{tc}">{icon}</span>'
        f'<span style="font-size:11px;font-weight:700;color:{tc}">{difficulty}</span>'
        f'</div>'
    )

def _build_rec_cards_html(recommendations: list) -> str:
    if not recommendations:
        return (
            '<div class="flex flex-col items-center justify-center h-32 text-center">'
            '<div style="font-size:2.5rem;margin-bottom:8px;">🎯</div>'
            '<p class="font-body-sm text-body-sm text-secondary">No recommendations yet.<br>Try exploring more activities!</p>'
            "</div>"
        )
    cards = []
    for rec in recommendations:
        act = rec.get("activity", {})
        act_id = act.get("id", 0)
        title = _escape_html(act.get("title", ""))
        atype = act.get("activity_type", "other").lower()
        color = _HP_TYPE_COLORS.get(atype, "#5f5e5e")
        emoji = _HP_EMOJI_MAP.get(atype, "🎯")
        ai_insight = _escape_html(rec.get("ai_insight", ""))
        spots_left = rec.get("spots_left", 0)
        is_joined = rec.get("is_joined", False)
        current = act.get("current_participants", 0)
        try:
            _sd = datetime.fromisoformat(act.get("start_time", ""))
            _et_raw = act.get("end_time") or ""
            _end_suffix = ""
            if _et_raw:
                try:
                    _end_suffix = "–" + datetime.fromisoformat(_et_raw).strftime("%H:%M")
                except Exception:
                    pass
            time_str = _sd.strftime("%a, %b %d · %H:%M") + _end_suffix
        except Exception:
            time_str = ""
        location = _escape_html(act.get("location", ""))
        difficulty = act.get("difficulty") or ""
        type_label = atype.replace("_", " ").title()
        tl_badge = _difficulty_badge(difficulty) if difficulty else (
            f'<div class="absolute top-3 left-3 bg-white px-3 py-1 rounded-full flex items-center space-x-1 shadow-sm">'
            f'<span class="material-symbols-outlined" style="font-size:14px;color:#FF385C;font-variation-settings:\'FILL\' 1;">bolt</span>'
            f'<span style="font-size:12px;font-weight:600;color:#FF385C">{type_label}</span>'
            f'</div>'
        )
        if is_joined:
            btn_html = '<button disabled class="w-full py-3 rounded-lg cursor-default" style="background:#EDFAF3;color:#1A7A4A;border:1px solid #B8EDD3;font-size:14px;font-weight:600;">✓ Joined</button>'
        elif spots_left > 0:
            btn_html = f'<button onclick="joinActivity({act_id})" class="w-full py-3 bg-rausch text-white rounded-lg hover:bg-rausch-active transition-all" style="font-size:14px;font-weight:600;">Join Activity</button>'
        else:
            btn_html = '<button disabled class="w-full py-3 rounded-lg cursor-default" style="background:#EFEDED;color:#5f5e5e;font-size:14px;font-weight:600;">Full</button>'
        cards.append(
            f'<div class="bg-canvas border border-hairline rounded-xl overflow-hidden group transition-all duration-300 p-4 space-y-4">'
            # Image area with badge
            f'<div class="relative h-48 rounded-lg overflow-hidden flex items-center justify-center" style="background:linear-gradient(135deg,{color}33,{color}15);">'
            f'<span style="font-size:4rem;">{emoji}</span>'
            + tl_badge
            + '</div>'
            # Info
            f'<div class="space-y-1">'
            f'<h3 style="font-size:18px;font-weight:700;color:#222222;margin:0">{title}</h3>'
            f'<div class="flex items-center space-x-2" style="color:#5f5e5e;font-size:14px;margin-top:4px">'
            f'<div class="flex items-center space-x-1"><span class="material-symbols-outlined" style="font-size:18px">group</span><span>{current}</span></div>'
            f'<span>•</span><span>{time_str}</span>'
            f'</div>'
            + (f'<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:14px;margin-top:2px">'
               f'<span class="material-symbols-outlined" style="font-size:18px">location_on</span>'
               f'<span style="text-transform:capitalize">{location}</span></div>' if location else '')
            + f'</div>'
            # Insight
            f'<div class="bg-surface-soft p-3 rounded-lg" style="border:1px solid rgba(221,221,221,0.5)">'
            f'<p style="margin:0;font-size:13px;color:#5f5e5e">{ai_insight}</p>'
            f'</div>'
            + btn_html
            + '</div>'
        )
    return "\n".join(cards)



def _build_browse_cards_html(items: list, current_user_id: int) -> str:
    if not items:
        return (
            '<div class="flex flex-col items-center justify-center h-48 text-center">'
            '<div style="font-size:2.5rem;margin-bottom:8px;">🔍</div>'
            '<p style="font-size:14px;color:#5f5e5e">No activities found.</p>'
            '</div>'
        )
    cards = []
    for item in items:
        src = item.get("source", "user_created")
        loc_type = item.get("location_type", "off_campus")
        title = _escape_html(item.get("title", ""))
        atype = item.get("activity_type", "other").lower()
        color = _HP_TYPE_COLORS.get(atype, "#5f5e5e")
        emoji = _HP_EMOJI_MAP.get(atype, "🎯")
        _st_raw = item.get("start_time", "")
        _et_raw = item.get("end_time") or ""
        start_time = _escape_html(_st_raw + (f"–{_et_raw}" if _et_raw else ""))
        location = _escape_html(item.get("location", ""))
        host_name = _escape_html(item.get("host_name") or ("Platform" if src == "platform" else ""))
        spots_left = item.get("spots_left", 0)
        is_joined = item.get("is_joined", False)
        act_id = item.get("id", 0)
        created_by = item.get("created_by")

        difficulty = item.get("difficulty") or ""
        top_left_badge = _difficulty_badge(difficulty) if difficulty else ""

        _btn_base = 'width:100%;height:44px;border-radius:8px;font-size:14px;font-weight:600;border:none;box-sizing:border-box;cursor:'
        is_free_facility = item.get("is_free_facility", False)
        if is_free_facility:
            btn_html = f'<div style="{_btn_base}default;background:#F7F7F7;color:#5f5e5e;display:flex;align-items:center;justify-content:center;gap:6px;border-radius:8px;"><span class="material-symbols-outlined" style="font-size:18px">door_open</span>Walk-in · Miễn phí</div>'
        elif is_joined:
            btn_html = f'<button disabled style="{_btn_base}default;background:#EDFAF3;color:#1A7A4A;">✓ Joined</button>'
        elif spots_left > 0:
            if src == "platform":
                btn_html = f'<button onclick="joinGymClass({act_id})" style="{_btn_base}pointer;background:#FF385C;color:#fff;">Join</button>'
            else:
                btn_html = f'<button onclick="joinActivity({act_id})" style="{_btn_base}pointer;background:#FF385C;color:#fff;">Join Activity</button>'
        else:
            btn_html = f'<button disabled style="{_btn_base}default;background:#EFEDED;color:#5f5e5e;">Full</button>'

        # Delete: icon button overlaid top-right of image — no extra height
        delete_overlay = ""
        if src == "user_created" and created_by == current_user_id:
            delete_overlay = (
                f'<button onclick="event.stopPropagation();deleteActivity({act_id},this)" '
                f'title="Delete" '
                f'style="position:absolute;top:10px;right:10px;width:28px;height:28px;border-radius:50%;'
                f'background:rgba(255,255,255,0.9);border:none;cursor:pointer;display:flex;align-items:center;'
                f'justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,0.15)">'
                f'<span class="material-symbols-outlined" style="font-size:16px;color:#c0392b">delete</span>'
                f'</button>'
            )

        cards.append(
            f'<div class="bg-canvas border border-hairline rounded-xl overflow-hidden transition-all duration-300 p-4 space-y-4"'
            f' data-source="{src}" data-location-type="{loc_type}">'
            # Image area
            f'<div class="relative h-40 rounded-lg overflow-hidden flex items-center justify-center" style="background:linear-gradient(135deg,{color}33,{color}15);">'
            f'<span style="font-size:3.5rem;">{emoji}</span>'
            # Difficulty badge (top-left, only if set)
            + top_left_badge
            # Delete icon overlay (top-right, own activities only)
            + delete_overlay
            + '</div>'
            # Info
            f'<div class="space-y-1">'
            f'<h3 style="font-size:16px;font-weight:700;color:#222222;margin:0">{title}</h3>'
            + (f'<div style="font-size:13px;color:#5f5e5e">{start_time}</div>' if start_time else '')
            + (f'<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:13px">'
               f'<span class="material-symbols-outlined" style="font-size:16px">location_on</span>'
               f'<span style="text-transform:capitalize">{location}</span></div>' if location else '')
            + (f'<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:13px">'
               f'<span class="material-symbols-outlined" style="font-size:16px">person</span>'
               f'<span>{host_name}</span></div>' if host_name else '')
            + f'</div>'
            + btn_html
            + '</div>'
        )
    return "\n".join(cards)


def _build_main_component_html(user_name: str, recommendations: list, user_id: int, initial_view: str = 'agent', user: dict = None, browse_items: list = None) -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/homepage_discover_afterwork_mascot_logo/code.html")) as f:
        html = f.read()
    with open(os.path.join(_dir, "design/discover_activities_afterwork_agent/code.html")) as f:
        dsc_html = f.read()

    # Replace expired mascot image URLs with Material Symbol icon
    html = _fix_mascot(html)

    # ── Fixed-layout + discover-specific CSS ─────────────────────────────────
    html = html.replace("</style>",
        """/* ── iframe fixed-layout ── */
        html,body{height:100%;overflow:hidden;margin:0;padding:0;}
        body>div.flex{position:fixed!important;inset:0!important;}
        /* discover spacing/custom classes not in homepage tailwind config */
        .px-grid-margin{padding-left:80px;padding-right:80px;}
        .pb-section-padding{padding-bottom:80px;}
        .py-section-padding{padding-top:80px;padding-bottom:80px;}
        .filter-pill{box-shadow:0 1px 2px rgba(0,0,0,0.08),0 4px 12px rgba(0,0,0,0.05);}
        .activity-card-shadow:hover{box-shadow:0 6px 16px rgba(0,0,0,0.12);}
        #view-discover{ flex-direction:column;}
        #view-discover .max-w-5xl{max-width:64rem;}
        #view-discover header{position:sticky;top:0;z-index:40;backdrop-filter:blur(12px);padding:24px 80px;}
        /* view switching — JS controls display via inline style; no !important here */
        #view-agent,#view-discover,#for-you-panel{transition:none;}
        @keyframes _typing{0%,100%{opacity:0.3;transform:scale(0.8);}50%{opacity:1;transform:scale(1.1);}}
        @keyframes _msg_in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes _skel_shine{0%{background-position:-200% 0}100%{background-position:200% 0}}
        .skel-line{border-radius:8px;background:linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);background-size:200% 100%;animation:_skel_shine 1.2s infinite linear;}
        @media(max-width:767px){
          .px-grid-margin{padding-left:16px!important;padding-right:16px!important;}
          .py-section-padding{padding-top:32px!important;padding-bottom:32px!important;}
          .pb-section-padding{padding-bottom:32px!important;}
          #view-discover header{padding:16px!important;}
          #view-discover{padding-bottom:64px;}
          #view-create{padding:16px 16px 72px!important;}
          #view-profile{padding-bottom:64px;}
          #hp-chat-scroll{padding-bottom:16px!important;}
          #hp-chat-input-area{padding-bottom:72px!important;}
          #dsc-fab{bottom:4.5rem!important;}
        }
        </style>""", 1)

    # ── Sidebar nav: both start inactive; JS sets active via updateNavActive ───
    html = html.replace(
        '<a class="flex items-center space-x-3 px-stack-md py-3 bg-surface-soft text-rausch rounded-lg transition-all duration-200" href="#">\n<span class="material-symbols-outlined" style="font-variation-settings: &quot;FILL&quot; 1;">explore</span>\n<span class="font-nav-link text-nav-link">Discover</span>\n</a>',
        '<a class="flex items-center space-x-3 px-stack-md py-3 text-secondary hover:bg-surface-soft hover:text-ink rounded-lg transition-all duration-200" href="#">\n<span class="material-symbols-outlined">explore</span>\n<span id="nav-discover" class="font-nav-link text-nav-link">Discover</span>\n</a>',
    )
    _mascot_nav_icon = f'<img src="{_MASCOT_DATA_URI}" style="width:20px;height:20px;object-fit:cover;border-radius:50%;">' if _MASCOT_DATA_URI else '<span class="material-symbols-outlined">smart_toy</span>'
    html = html.replace(
        '<a class="flex items-center space-x-3 px-stack-md py-3 text-secondary hover:bg-surface-soft hover:text-ink rounded-lg transition-all duration-200" href="#">\n<span class="material-symbols-outlined">smart_toy</span>\n<span class="font-nav-link text-nav-link">My Agent</span>\n</a>',
        f'<a class="flex items-center space-x-3 px-stack-md py-3 text-secondary hover:bg-surface-soft hover:text-ink rounded-lg transition-all duration-200" href="#">\n{_mascot_nav_icon}\n<span id="nav-agent" class="font-nav-link text-nav-link">My Agent</span>\n</a>',
    )
    html = html.replace(
        '<span class="font-nav-link text-nav-link">Create Your Activity</span>',
        '<span id="nav-create" class="font-nav-link text-nav-link">Create Your Activity</span>',
    )
    html = html.replace(
        '<span class="font-nav-link text-nav-link">Profile</span>',
        '<span id="nav-profile" class="font-nav-link text-nav-link">Profile</span>',
    )
    html = html.replace(
        '<button class="w-full flex items-center justify-center space-x-2 bg-rausch text-white py-3 rounded-lg font-button-md hover:bg-rausch-active transition-all shadow-sm">',
        '<button id="btn-new-chat" onclick="newChat()" class="w-full flex items-center justify-center space-x-2 bg-rausch text-white py-3 rounded-lg font-button-md hover:bg-rausch-active transition-all shadow-sm">',
    )
    html = html.replace(
        '<div class="space-y-1"><a href="#" class="flex items-center space-x-3 py-2 text-secondary hover:text-ink transition-colors group"><span class="material-symbols-outlined text-[18px]">chat_bubble</span><span class="text-body-sm truncate">Football match tonight</span></a><a href="#" class="flex items-center space-x-3 py-2 text-secondary hover:text-ink transition-colors group"><span class="material-symbols-outlined text-[18px]">chat_bubble</span><span class="text-body-sm truncate">Yoga class booking</span></a><a href="#" class="flex items-center space-x-3 py-2 text-secondary hover:text-ink transition-colors group"><span class="material-symbols-outlined text-[18px]">chat_bubble</span><span class="text-body-sm truncate">Product team lunch</span></a></div>',
        '<div id="recents-list" class="space-y-1"></div>',
    )

    # ── Greeting ──────────────────────────────────────────────────────────────
    # ── Greeting icon: smart_toy → mascot ────────────────────────────────────
    _mascot_greeting = (
        f'<img src="{_MASCOT_DATA_URI}" style="width:48px;height:48px;object-fit:cover;border-radius:50%;">'
        if _MASCOT_DATA_URI else
        '<span class="material-symbols-outlined" style="font-variation-settings: &quot;FILL&quot; 1;">smart_toy</span>'
    )
    html = html.replace(
        '<div class="w-12 h-12 bg-surface-container rounded-full flex items-center justify-center text-rausch">\n<span class="material-symbols-outlined" style="font-variation-settings: &quot;FILL&quot; 1;">smart_toy</span>\n</div>',
        f'<div class="w-12 h-12 rounded-full overflow-hidden flex items-center justify-center">{_mascot_greeting}</div>',
    )

    html = html.replace(
        "Hi An! What are you in the mood for after work today?",
        f"Hi {_escape_html(user_name)}! What are you in the mood for after work today?",
    )

    # ── Chat scroll area / messages / chips / input ───────────────────────────
    html = html.replace(
        '<div class="flex-1 overflow-y-auto no-scrollbar p-stack-xl flex flex-col items-center">',
        '<div id="hp-chat-scroll" class="flex-1 overflow-y-auto no-scrollbar p-stack-xl flex flex-col items-center">',
    )
    html = html.replace(
        "<!-- Suggested Chips Area -->",
        '<div id="hp-chat-messages" class="w-full"></div>',
    )
    html = html.replace(
        'placeholder="Type to chat with ALP..." rows="1">',
        'id="hp-chat-input" placeholder="Type to chat with ALP..." rows="1" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">',
    )
    html = html.replace(
        '<button class="ml-2 w-10 h-10 bg-rausch text-white rounded-full flex items-center justify-center hover:bg-rausch-active transition-all shrink-0">',
        '<button id="hp-send-btn" class="ml-2 w-10 h-10 bg-rausch text-white rounded-full flex items-center justify-center hover:bg-rausch-active transition-all shrink-0">',
    )
    html = html.replace(
        '<!-- Chat Input Area -->\n<div class="p-stack-lg bg-canvas">',
        '<!-- Chat Input Area -->\n<div id="hp-chat-input-area" class="p-stack-lg bg-canvas">',
    )

    # ── For You aside: add id + start hidden, JS shows it in agent view only ─
    html = html.replace(
        '<aside class="w-96 bg-surface border-l border-hairline hidden lg:flex flex-col">',
        '<aside id="for-you-panel" class="w-96 bg-surface border-l border-hairline flex-col" style="display:none">',
    )

    # ── For You cards (server-side) ───────────────────────────────────────────
    _cards = _build_rec_cards_html(recommendations)
    html = re.sub(
        r'<div class="flex-1 overflow-y-auto no-scrollbar px-stack-lg space-y-stack-lg pb-stack-xl">.*?</div>\s*</aside>',
        f'<div id="fy-cards" class="flex-1 overflow-y-auto no-scrollbar px-stack-lg space-y-stack-lg pb-stack-xl">{_cards}</div>\n</aside>',
        html, flags=re.DOTALL,
    )

    # ── Wrap agent view (main + For You aside) in #view-agent ─────────────────
    html = html.replace(
        '</aside>\n<!-- CENTER PANEL: Conversational Interface -->',
        '</aside>\n<div id="view-agent" style="display:flex;flex:1;min-width:0;overflow:hidden">\n<!-- CENTER PANEL: Conversational Interface -->',
    )

    # ── Extract discover main content (no sidebar, no footer) ─────────────────
    dsc_m = re.search(r'<!-- Main Content Area -->\n<main[^>]*>(.*?)</main>', dsc_html, re.DOTALL)
    dsc_inner = dsc_m.group(1) if dsc_m else ''
    dsc_inner = re.sub(r'<!-- Footer Shell -->.*?</footer>', '', dsc_inner, flags=re.DOTALL)
    _browse_items = browse_items or []
    _browse_cards = _build_browse_cards_html(_browse_items, user_id)
    _filter_tabs = (
        '<div style="display:flex;gap:8px;margin-bottom:24px">'
        '<button id="filter-all" onclick="filterBrowse(\'all\')" style="padding:6px 16px;border-radius:999px;border:2px solid #222;background:#222;color:#fff;font-size:13px;font-weight:600;cursor:pointer">All</button>'
        '<button id="filter-on" onclick="filterBrowse(\'on_campus\')" style="padding:6px 16px;border-radius:999px;border:1px solid #ddd;background:#fff;color:#5f5e5e;font-size:13px;font-weight:600;cursor:pointer">On Campus</button>'
        '<button id="filter-off" onclick="filterBrowse(\'off_campus\')" style="padding:6px 16px;border-radius:999px;border:1px solid #ddd;background:#fff;color:#5f5e5e;font-size:13px;font-weight:600;cursor:pointer">Off Campus</button>'
        '</div>'
    )
    dsc_inner = re.sub(
        r'<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-10">.*?</div>\s*</section>',
        f'{_filter_tabs}<div id="browse-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-6">{_browse_cards}</div>\n</section>',
        dsc_inner, flags=re.DOTALL,
    )
    discover_view = (
        '<div id="view-discover" style="display:none;flex:1;min-width:0;overflow-y:auto">'
        + dsc_inner
        + '<div id="dsc-fab" style="position:fixed;bottom:2rem;right:2rem;z-index:50">'
          '<button id="dsc-alp-btn" class="w-14 h-14 bg-rausch rounded-full flex items-center justify-center shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95">'
          '<span class="material-symbols-outlined text-white" style="font-size:28px">auto_awesome</span>'
          '</button></div>'
        '</div>'
    )

    # ── Create activity view (embedded, pure JS routing, no page reload) ──────
    with open(os.path.join(_dir, "design/create_your_activity_afterwork_agent/code.html")) as _cf:
        _ca_html = _cf.read()
    _ca_m = re.search(r'<main[^>]*>(.*?)</main>', _ca_html, re.DOTALL)
    _ca_inner = _ca_m.group(1).strip() if _ca_m else ''
    _today_str = date.today().isoformat()
    _ca_inner = _ca_inner.replace('type="date">', f'type="date" id="ca-date" value="{_today_str}">', 1)
    _ca_inner = _ca_inner.replace(
        '>schedule</span>\n</div>',
        ' id="ca-start" value="18:00">schedule</span>\n</div>', 1,
    )
    _ca_inner = re.sub(r'type="time">', 'type="time" id="ca-start" value="18:00">', _ca_inner, count=1)
    _ca_inner = re.sub(r'type="time">', 'type="time" id="ca-end" value="19:00">', _ca_inner, count=1)
    create_view = (
        '<div id="view-create" style="display:none;flex:1;min-width:0;overflow-y:auto;background:#fbf9f8; padding: 5rem;">'
        + _ca_inner
        + '</div>'
    )

    # ── Profile view (embedded, pure JS routing, no page reload) ─────────────
    _pf_user = user or {}
    _pf_full_name = _escape_html(_pf_user.get("full_name") or _pf_user.get("domain", user_name))
    _pf_domain = _escape_html(_pf_user.get("domain", ""))
    _pf_title = _escape_html(_pf_user.get("title") or "Employee")
    _pf_company = _escape_html(_pf_user.get("company") or "—")
    _pf_dept = _escape_html(_pf_user.get("department") or "—")
    _pf_group = _escape_html(_pf_user.get("org_group") or "—")
    _pf_squad = _escape_html(_pf_user.get("squad") or "—")
    _pf_ints = _pf_user.get("interests", [])
    _pf_initial = (_pf_full_name[0] if _pf_full_name else "?").upper()
    _pf_pct = 50
    if _pf_user.get("full_name"): _pf_pct += 10
    if _pf_user.get("company"):   _pf_pct += 5
    if _pf_user.get("department"): _pf_pct += 5
    if _pf_user.get("org_group"):  _pf_pct += 5
    if _pf_ints:                   _pf_pct += 20
    _pf_pct = min(_pf_pct, 100)
    _pf_tip = "Add more details to unlock better recommendations." if _pf_pct < 100 else "Your profile is looking great!"

    with open(os.path.join(_dir, "design/my_profile_afterwork_agent/code.html")) as _pff:
        _pf_html = _fix_mascot(_pff.read())
    _pf_m = re.search(r'<main[^>]*>(.*?)</main>', _pf_html, re.DOTALL)
    _pf_inner = _pf_m.group(1).strip() if _pf_m else ''
    _pf_inner = re.sub(r'<footer[^>]*>.*?</footer>', '', _pf_inner, flags=re.DOTALL)
    # data replacements
    _pf_inner = _pf_inner.replace(
        '<img alt="Nguyen Thanh An Profile Avatar" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBmWfvsLyu_azF3tdLua1Ab-8Cdz8q371_ss07Y23Stqxq-TWSO5vWJhK2fSHIqPma-SEY8RzZuFqATQUxyTVYTCvNNzvUnueuKsORGER6qo0A_BSScZFnaycsOcDSv-guzq_p-yEhk0dxmSTspSBFiteryywLe8z1DSMp5r5v5vC8nYTgV8zMMel3RyWKSMe-gyANz5_NjHHt-NuQ0ty4WLe2C9zeecFaXN6kCZpWzNcn02scqhiOum3ztwUdHFHf_R5QBQjOAlFc">',
        f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#FF385C,#c90034);font-size:48px;font-weight:700;color:#fff;">{_pf_initial}</div>',
    )
    _pf_inner = _pf_inner.replace(
        '<button class="absolute bottom-0 right-0 p-2 bg-white border border-hairline rounded-full shadow-md hover:scale-110 transition-transform">\n<span class="material-symbols-outlined text-rausch text-[18px]">photo_camera</span>\n</button>', '')
    _pf_inner = _pf_inner.replace(
        '<h2 class="font-display-xl text-display-xl text-ink">Nguyen Thanh An</h2>',
        f'<h2 class="font-display-xl text-display-xl text-ink">{_pf_full_name}</h2>')
    _pf_inner = _pf_inner.replace(
        '<p class="font-body-md text-body-md text-secondary">Senior Software Engineer</p>',
        f'<p class="font-body-md text-body-md text-secondary">{_pf_title} · @{_pf_domain}</p>')
    _pf_inner = _pf_inner.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Full Name</label>\n'
        '<p class="font-body-md text-body-md text-ink">Nguyen Thanh An</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Full Name</label>\n'
        f'<p class="font-body-md text-body-md text-ink">{_pf_full_name}</p>')
    _pf_inner = _pf_inner.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">domain</label>\n'
        '<p class="font-body-md text-body-md text-ink">annt7</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Domain</label>\n'
        f'<p class="font-body-md text-body-md text-ink">@{_pf_domain}</p>')
    _pf_inner = _pf_inner.replace('>6 April 1995<', '>—<')
    _pf_inner = _pf_inner.replace('>Aries<', '>—<')
    _pf_inner = _pf_inner.replace('>ZP<', f'>{_pf_company}<')
    _pf_inner = _pf_inner.replace('>&nbsp;N/A<', f'>&nbsp;{_pf_dept}<')
    _pf_inner = _pf_inner.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-3">Group</label>\n'
        '<p class="font-display-md text-display-md text-ink">N/A</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-3">Group</label>\n'
        f'<p class="font-display-md text-display-md text-ink">{_pf_group}</p>')
    _pf_inner = _pf_inner.replace('>Consumer Solutions<', f'>{_pf_squad}<')
    _pf_iicons = {
        "football":"sports_soccer","running":"sprint","gym":"fitness_center",
        "swimming":"pool","taekwondo":"sports_martial_arts","badminton":"sports_tennis",
        "ai":"smart_toy","product":"inventory_2","english":"translate",
        "movies":"movie","board games":"casino","coffee chat":"local_cafe",
        "karaoke":"mic","yoga":"self_improvement","zumba":"music_note",
        "pickleball":"sports_tennis","dining":"restaurant","picnic":"park",
        "book club":"menu_book",
    }
    _pf_pills = "".join([
        f'<span class="px-5 py-2.5 rounded-full border border-hairline bg-white flex items-center gap-2" style="cursor:default">'
        f'<span class="material-symbols-outlined text-[18px]">{_pf_iicons.get(i.lower(),"star")}</span>'
        f'{_escape_html(i.capitalize())}</span>'
        for i in _pf_ints
    ])
    _pf_pills += ('<button onclick="showInterestModal()" class="px-5 py-2.5 rounded-full border border-dashed'
                  ' border-secondary text-secondary hover:border-ink hover:text-ink flex items-center gap-2 transition-all">'
                  '<span class="material-symbols-outlined text-[18px]">add</span>Add New</button>')
    _pf_inner = re.sub(
        r'<div class="flex flex-wrap gap-3">.*?</div>(?=\s*</section>)',
        f'<div class="flex flex-wrap gap-3">{_pf_pills}</div>',
        _pf_inner, flags=re.DOTALL, count=1)
    _pf_inner = _pf_inner.replace(
        '<button class="text-rausch font-button-md text-body-sm hover:underline">Manage Interests</button>',
        '<button onclick="showInterestModal()" class="text-rausch font-button-md text-body-sm hover:underline">Manage Interests</button>')
    _pf_inner = _pf_inner.replace('<span class="font-nav-link text-ink">85%</span>', f'<span class="font-nav-link text-ink">{_pf_pct}%</span>')
    _pf_inner = _pf_inner.replace('style="width: 85%"', f'style="width:{_pf_pct}%"')
    _pf_inner = _pf_inner.replace(
        "<p class=\"mt-4 font-caption text-caption text-secondary\">Add a 'Personal Bio' to reach 100% and unlock more personalized agent recommendations.</p>",
        f'<p class="mt-4 font-caption text-caption text-secondary">{_pf_tip}</p>')

    _pf_all_ints = ["football","running","gym","swimming","badminton","ai","product",
                    "english","movies","board games","coffee chat","karaoke","yoga",
                    "zumba","pickleball","dining","book club"]
    _pf_int_lower = [i.lower() for i in _pf_ints]
    _pf_modal_checks = "".join([
        f'<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;cursor:pointer;">'
        f'<input type="checkbox" class="pf-int-cb" value="{i}" {"checked" if i in _pf_int_lower else ""}'
        f' style="accent-color:#FF385C;width:16px;height:16px;">'
        f'<span class="material-symbols-outlined" style="font-size:18px;color:#5f5e5e;">{_pf_iicons.get(i,"star")}</span>'
        f'<span style="font-size:14px;color:#222;">{i.capitalize()}</span></label>'
        for i in _pf_all_ints
    ])
    _pf_modal = (
        '<div id="interest-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:9999;align-items:center;justify-content:center;">'
        '<div style="background:#fff;border-radius:16px;max-width:480px;width:90%;max-height:80vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.15);">'
        '<div style="padding:20px 24px;border-bottom:1px solid #DDDDDD;display:flex;justify-content:space-between;align-items:center;">'
        '<h3 style="font-size:18px;font-weight:600;color:#222;margin:0;">Manage Interests</h3>'
        '<button onclick="hideInterestModal()" style="background:none;border:none;cursor:pointer;font-size:22px;color:#5f5e5e;line-height:1;">✕</button>'
        '</div>'
        f'<div style="overflow-y:auto;padding:8px 12px;flex:1;display:grid;grid-template-columns:1fr 1fr;gap:2px;">{_pf_modal_checks}</div>'
        '<div style="padding:16px 24px;border-top:1px solid #DDDDDD;">'
        '<button onclick="saveInterests()" style="background:#FF385C;color:#fff;border:none;cursor:pointer;width:100%;padding:12px;border-radius:8px;font-size:16px;font-weight:600;">Save Interests</button>'
        '</div></div></div>'
    )
    _pf_signout = (
        '<div style="padding:32px 40px 48px;">'
        '<button onclick="localStorage.removeItem(\'aw_auth_session\');Streamlit.setComponentValue({action:\'logout\'})" '
        'style="display:flex;align-items:center;gap:10px;padding:12px 20px;border:1px solid #DDDDDD;'
        'border-radius:8px;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#5f5e5e;'
        'transition:all 0.15s;" '
        'onmouseover="this.style.borderColor=\'#FF385C\';this.style.color=\'#FF385C\'" '
        'onmouseout="this.style.borderColor=\'#DDDDDD\';this.style.color=\'#5f5e5e\'">'
        '<span class="material-symbols-outlined" style="font-size:18px;">logout</span>'
        'Sign Out'
        '</button>'
        '</div>'
    )
    profile_view = (
        f'<div id="view-profile" style="display:none;flex:1;min-width:0;overflow-y:auto;background:#fbf9f8;">'
        f'{_pf_inner}'
        f'{_pf_signout}'
        f'</div>'
        f'{_pf_modal}'
    )

    # ── Close #view-agent, inject discover + create + profile views, re-close outer flex ─
    html = html.replace(
        '</aside>\n</div>\n<!-- Footer for Mobile V',
        f'</aside>\n</div>\n{discover_view}\n{create_view}\n{profile_view}\n</div>\n<!-- Footer for Mobile V',
    )

    # ── Mobile bottom nav: wire up onclick handlers ────────────────────────────
    html = re.sub(
        r'<footer class="md:hidden fixed bottom-0[^>]*>.*?</footer>',
        '<footer class="md:hidden fixed bottom-0 w-full bg-canvas border-t border-hairline py-2 flex justify-around items-center z-50">'
        '<a id="mnav-discover" class="flex flex-col items-center gap-0.5 px-3 py-1" href="#" onclick="showView(\'discover\');return false;">'
        '<span class="material-symbols-outlined text-[22px]">explore</span>'
        '<span class="text-[10px] font-medium">Discover</span></a>'
        '<a id="mnav-agent" class="flex flex-col items-center gap-0.5 px-3 py-1" href="#" onclick="showView(\'agent\');return false;">'
        '<span class="material-symbols-outlined text-[22px]">smart_toy</span>'
        '<span class="text-[10px] font-medium">Agent</span></a>'
        '<a id="mnav-create" class="flex flex-col items-center gap-0.5 px-3 py-1" href="#" onclick="showView(\'create\');return false;">'
        '<span class="material-symbols-outlined text-[22px]">add_circle</span>'
        '<span class="text-[10px] font-medium">Create</span></a>'
        '<a id="mnav-chat" class="flex flex-col items-center gap-0.5 px-3 py-1" href="#" onclick="showView(\'agent\');return false;">'
        '<span class="material-symbols-outlined text-[22px]">chat_bubble</span>'
        '<span class="text-[10px] font-medium">Chat</span></a>'
        '<a id="mnav-profile" class="flex flex-col items-center gap-0.5 px-3 py-1" href="#" onclick="showView(\'profile\');return false;">'
        '<span class="material-symbols-outlined text-[22px]">account_circle</span>'
        '<span class="text-[10px] font-medium">Profile</span></a>'
        '</footer>',
        html, flags=re.DOTALL
    )

    # ── Merged script: view-switching (pure JS) + chat + join ─────────────────
    new_script = f"""<script>
var Streamlit={{
  setComponentReady:function(){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1}},'*');}},
  setComponentValue:function(v){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:v}},'*');}},
  setFrameHeight:function(h){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h}},'*');}}
}};
Streamlit.setComponentReady();
(function(){{try{{var pd=window.parent.document;var _cov=pd.getElementById('_alp_tr_cover');if(_cov)_cov.parentNode.removeChild(_cov);if(!pd.getElementById('_alp_ol_kill')){{var s=pd.createElement('style');s.id='_alp_ol_kill';s.textContent='#_alp_main_overlay,#_alp_splash{{display:none!important}}';pd.head.appendChild(s);}}if(!pd.getElementById('_alp_chrome_css')){{var cs=pd.createElement('style');cs.id='_alp_chrome_css';cs.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{{display:none!important}}.main .block-container{{padding:0!important;max-width:100%!important}}[data-testid="stApp"],.stApp{{background:#FFF5F0!important}}';pd.head.appendChild(cs);}}}}catch(e){{}}}})();
(function setFH(){{
  var h=(window.parent&&window.parent.innerHeight)?window.parent.innerHeight:(window.screen?window.screen.availHeight:900);
  Streamlit.setFrameHeight(h);
}})();
window.addEventListener('resize',function(){{
  var h=(window.parent&&window.parent.innerHeight)?window.parent.innerHeight:900;
  Streamlit.setFrameHeight(h);
}});

// ── View switching (NO Streamlit rerun) ───────────────────────────────────
var USER_ID={user_id};
var BACKEND='{_BACKEND_URL}';
var CHAT_KEY='hp_chat_'+USER_ID;
var VIEW_KEY='aw_view_'+USER_ID;
var INITIAL_VIEW='{initial_view}';
var NAV_ACTIVE='flex items-center space-x-3 px-stack-md py-3 bg-surface-soft text-rausch rounded-lg transition-all duration-200';
var NAV_INACTIVE='flex items-center space-x-3 px-stack-md py-3 text-secondary hover:bg-surface-soft hover:text-ink rounded-lg transition-all duration-200';

function updateNavActive(v){{
  [['nav-discover','discover'],['nav-agent','agent'],['nav-create','create'],['nav-profile','profile']].forEach(function(p){{
    var span=document.getElementById(p[0]);if(!span)return;
    var a=span.closest('a');if(!a)return;
    var on=v===p[1];
    a.className=on?NAV_ACTIVE:NAV_INACTIVE;
    var ic=a.querySelector('.material-symbols-outlined');
    if(ic)ic.style.fontVariationSettings=on?'"FILL" 1':'"FILL" 0';
  }});
  [['mnav-discover','discover'],['mnav-agent','agent'],['mnav-create','create'],['mnav-chat','agent'],['mnav-profile','profile']].forEach(function(p){{
    var a=document.getElementById(p[0]);if(!a)return;
    var on=v===p[1];
    a.style.color=on?'#FF385C':'#5f5e5e';
    var ic=a.querySelector('.material-symbols-outlined');
    if(ic)ic.style.fontVariationSettings=on?'"FILL" 1':'"FILL" 0';
  }});
}}

function showView(v){{
  var ag=document.getElementById('view-agent');
  var ds=document.getElementById('view-discover');
  var cr=document.getElementById('view-create');
  var pf=document.getElementById('view-profile');
  var fy=document.getElementById('for-you-panel');
  if(ag)ag.style.display=v==='agent'?'flex':'none';
  if(ds)ds.style.display=v==='discover'?'block':'none';
  if(cr)cr.style.display=v==='create'?'block':'none';
  if(pf)pf.style.display=v==='profile'?'block':'none';
  if(fy)fy.style.display=v==='agent'?'flex':'none';
  try{{localStorage.setItem(VIEW_KEY,v);}}catch(e){{}}
  updateNavActive(v);
  if(v==='discover')refreshBrowseGrid(true);
}}

showView(INITIAL_VIEW);
refreshBrowseGrid();

// Nav clicks — discover/agent/create pure JS; profile → Streamlit
var _nd=document.getElementById('nav-discover');
if(_nd)_nd.closest('a').addEventListener('click',function(e){{e.preventDefault();showView('discover');}});
var _na=document.getElementById('nav-agent');
if(_na)_na.closest('a').addEventListener('click',function(e){{e.preventDefault();showView('agent');}});
var _nc=document.getElementById('nav-create');
if(_nc)_nc.closest('a').addEventListener('click',function(e){{e.preventDefault();showView('create');}});
var _np=document.getElementById('nav-profile');
if(_np)_np.closest('a').addEventListener('click',function(e){{e.preventDefault();showView('profile');}});
var _alp=document.getElementById('dsc-alp-btn');
if(_alp)_alp.addEventListener('click',function(){{showView('agent');}});

// ── Create Activity: location type toggle ─────────────────────────────────
function setLocationType(type){{
  var ltEl=document.getElementById('location-type');
  if(ltEl)ltEl.value=type;
  var sel=document.getElementById('location-select');
  var inp=document.getElementById('location-input');
  var btnOn=document.getElementById('btn-on-campus');
  var btnOff=document.getElementById('btn-off-campus');
  var activeAdd=['border-2','border-ink','bg-ink','text-canvas'];
  var activeRem=['border','border-hairline','text-secondary','hover:border-ink'];
  if(type==='on_campus'){{
    if(sel)sel.style.display='';if(inp)inp.style.display='none';
    if(btnOn){{activeAdd.forEach(function(c){{btnOn.classList.add(c);}});activeRem.forEach(function(c){{btnOn.classList.remove(c);}});}}
    if(btnOff){{activeAdd.forEach(function(c){{btnOff.classList.remove(c);}});activeRem.forEach(function(c){{btnOff.classList.add(c);}});}}
  }}else{{
    if(sel)sel.style.display='none';if(inp)inp.style.display='';
    if(btnOff){{activeAdd.forEach(function(c){{btnOff.classList.add(c);}});activeRem.forEach(function(c){{btnOff.classList.remove(c);}});}}
    if(btnOn){{activeAdd.forEach(function(c){{btnOn.classList.remove(c);}});activeRem.forEach(function(c){{btnOn.classList.add(c);}});}}
  }}
}}

// ── Toast notification ────────────────────────────────────────────────────
function showToast(msg){{
  var t=document.createElement('div');
  t.textContent=msg;
  t.style.cssText='position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#222;color:#fff;padding:12px 24px;border-radius:24px;font-size:14px;font-weight:600;z-index:9999;pointer-events:none;transition:opacity 0.4s';
  document.body.appendChild(t);
  setTimeout(function(){{t.style.opacity='0';}},2200);
  setTimeout(function(){{t.remove();}},2700);
}}

// ── Create Activity form ───────────────────────────────────────────────────
var _CA_EMOJI_MAP={{'football':'⚽','badminton':'🏸','swimming':'🏊','yoga':'🧘','gym':'🏋️','running':'🏃','board games':'🎲','dining':'🍽️','coffee':'☕','karaoke':'🎤','picnic':'🧺','ai':'🤖','product':'📦','book club':'📚','english':'🗣️','zumba':'💃','pickleball':'🏓'}};
var _CA_TYPE_MAP={{
  'Gym':'gym','Yoga':'yoga','Zumba':'zumba','Pickleball':'pickleball',
  'Badminton':'badminton','Football':'football','Running':'running',
  'Board Games':'board games','Dining':'dining','Coffee Chat':'coffee',
  'Karaoke':'karaoke','Picnics':'picnic','AI':'ai','Product':'product',
  'Book Club':'book club','English':'english','Swimming':'swimming'
}};
var _caSelLevel='';
document.querySelectorAll('#view-create .flex.gap-2 button[type="button"]').forEach(function(btn){{
  btn.addEventListener('click',function(){{
    _caSelLevel=this.textContent.trim();
    document.querySelectorAll('#view-create .flex.gap-2 button[type="button"]').forEach(function(b){{
      b.className='px-4 py-2 border border-hairline rounded-full font-body-sm text-body-sm hover:border-ink transition-colors';
    }});
    this.className='px-4 py-2 border border-ink bg-ink text-canvas rounded-full font-body-sm text-body-sm';
  }});
}});
var _caForm=document.querySelector('#view-create form');
if(_caForm)_caForm.addEventListener('submit',function(e){{
  e.preventDefault();
  var title=(document.getElementById('title')||{{}}).value||'';
  var type=(document.getElementById('type')||{{}}).value||'';
  var locType=(document.getElementById('location-type')||{{}}).value||'off_campus';
  var loc=locType==='on_campus'
    ?((document.getElementById('location-select')||{{}}).value||'')
    :((document.getElementById('location-input')||{{}}).value||'');
  var desc=(document.getElementById('description')||{{}}).value||'';
  var guide=(document.getElementById('guidelines')||{{}}).value||'';
  title=title.trim();loc=loc.trim();type=type.trim();
  if(!title||!loc||!type||type==='Choose Type'||loc==='Choose a campus venue'){{alert('Please fill in Activity Title, Activity Type, and Location.');return;}}
  var dateVal=(document.getElementById('ca-date')||{{}}).value||'';
  var startVal=(document.getElementById('ca-start')||{{}}).value||'18:00';
  var endVal=(document.getElementById('ca-end')||{{}}).value||'19:00';
  var grpEl=document.getElementById('participants');
  var grpText=grpEl?grpEl.value:'10 participants';
  var grpNum=grpText==='Unlimited'?100:(parseInt(grpText)||10);
  var actType=_CA_TYPE_MAP[type]||type.toLowerCase();
  var btn=e.target.querySelector('button[type="submit"]');
  if(btn){{btn.innerHTML='<span class="material-symbols-outlined" style="vertical-align:middle">sync</span> Posting...';btn.disabled=true;}}
  var startISO=dateVal+'T'+startVal+':00';
  var endISO=dateVal+'T'+endVal+':00';
  fetch(BACKEND+'/api/activities?creator_id='+USER_ID,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{
      title:title,activity_type:actType,location:loc,location_type:locType,
      description:desc,guidelines:guide||null,start_time:startISO,end_time:endISO,
      participant_limit:grpNum,difficulty:_caSelLevel||null
    }})
  }}).then(function(r){{
    if(!r.ok)throw new Error('server error '+r.status);
    return r.json();
  }}).then(function(act){{
    if(btn){{btn.innerHTML='<span class="material-symbols-outlined" style="vertical-align:middle">check_circle</span> Posted!';}}
    setTimeout(function(){{
      if(btn){{btn.innerHTML='Post Activity';btn.disabled=false;}}
      _caForm.reset();_caSelLevel='';
      setLocationType('on_campus');
    }},1800);
    // Add new card to discover grid
    var grid=document.getElementById('browse-grid');
    if(grid){{
      var em=_CA_EMOJI_MAP[actType]||'🎯';
      var dtLabel='';
      if(dateVal){{var dp=dateVal.split('-');dtLabel=new Date(dp[0],dp[1]-1,dp[2]).toLocaleDateString('en-GB',{{day:'numeric',month:'short'}})+' · '+startVal+'–'+endVal;}}
      var diffBadge='';
      if(_caSelLevel){{
        var diffColors={{'Beginner':'#E8F5E9','Intermediate':'#FFF3E0','Advanced':'#FCE4EC','All Levels':'#F3E5F5'}};
        var diffText={{'Beginner':'#2E7D32','Intermediate':'#E65100','Advanced':'#C62828','All Levels':'#6A1B9A'}};
        diffBadge='<div style="position:absolute;top:12px;left:12px;padding:3px 10px;border-radius:999px;display:inline-flex;align-items:center;gap:4px;background:'+diffColors[_caSelLevel]+'"><span style="font-size:11px;font-weight:700;color:'+diffText[_caSelLevel]+'">'+_caSelLevel+'</span></div>';
      }}
      var card=document.createElement('div');
      card.className='bg-canvas border border-hairline rounded-xl overflow-hidden transition-all duration-300 p-4 space-y-4';
      card.setAttribute('data-source','user_created');
      card.setAttribute('data-location-type',locType);
      card.innerHTML='<div class="relative h-40 rounded-lg overflow-hidden flex items-center justify-center" style="background:linear-gradient(135deg,#FF385C33,#FF385C15)">'+
        '<span style="font-size:3.5rem">'+em+'</span>'+diffBadge+
        '<button onclick="event.stopPropagation();deleteActivity('+act.id+',this)" title="Delete" style="position:absolute;top:10px;right:10px;width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.9);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,0.15)"><span class="material-symbols-outlined" style="font-size:16px;color:#c0392b">delete</span></button></div>'+
        '<div class="space-y-1"><h3 style="font-size:16px;font-weight:700;color:#222222;margin:0">'+title+'</h3>'+
        '<div style="font-size:13px;color:#5f5e5e">'+dtLabel+'</div>'+
        '<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:13px"><span class="material-symbols-outlined" style="font-size:16px">location_on</span><span style="text-transform:capitalize">'+loc+'</span></div></div>'+
        '<button disabled style="width:100%;height:44px;border-radius:8px;font-size:14px;font-weight:600;border:none;box-sizing:border-box;cursor:default;background:#EDFAF3;color:#1A7A4A;">✓ Joined</button>';
      grid.prepend(card);
    }}
    showToast('Activity posted!');
    showView('discover');
  }}).catch(function(err){{
    console.error('Create activity error:',err);
    if(btn){{btn.innerHTML='Post Activity';btn.disabled=false;}}
    alert('Failed to post activity. Please try again.');
  }});
}});

// ── Client-side chat ───────────────────────────────────────────────────────
var SESSIONS_KEY='aw_sessions_'+USER_ID;
var chatHistory=[];
try{{chatHistory=JSON.parse(localStorage.getItem(CHAT_KEY)||'[]');}}catch(e){{chatHistory=[];}}
var _chatSending=false;
var _activeSessionId=null; // set when loading a saved session; cleared on first new message

function renderMessages(animate){{
  var container=document.getElementById('hp-chat-messages');
  if(!container)return;
  var welcome=document.getElementById('hp-welcome');
  if(welcome)welcome.style.display=chatHistory.length>0?'none':'flex';
  container.innerHTML='';
  chatHistory.forEach(function(msg,idx){{
    var wrap=document.createElement('div');
    wrap.className='flex items-start gap-3 mb-4'+(msg.role==='user'?' flex-row-reverse':'');
    if(animate){{
      wrap.style.cssText='opacity:0;animation:_msg_in 0.28s ease forwards;animation-delay:'+(idx*55)+'ms';
    }}
    if(msg.role==='assistant'){{
      var av=document.createElement('div');
      av.style.cssText='width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px;overflow:hidden;background:#EFEDED';
      var _mi=document.createElement('img');_mi.src='{_MASCOT_DATA_URI}';_mi.style.cssText='width:100%;height:100%;object-fit:cover;';av.appendChild(_mi);
      wrap.appendChild(av);
    }}
    var bubble=document.createElement('div');
    bubble.style.cssText='max-width:80%;padding:12px;border-radius:12px;background:'+(msg.role==='user'?'#222222':'#F7F7F7')+';border:1px solid '+(msg.role==='user'?'#222222':'#DDDDDD');
    var p=document.createElement('p');
    p.style.cssText='margin:0;font-size:14px;line-height:1.5;white-space:pre-wrap;color:'+(msg.role==='user'?'#FFFFFF':'#222222');
    if(msg.role==='assistant'){{
      var _esc=msg.content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      p.innerHTML=_esc.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    }}else{{p.textContent=msg.content;}}
    bubble.appendChild(p);wrap.appendChild(bubble);
    container.appendChild(wrap);
  }});
  var scroll=document.getElementById('hp-chat-scroll');
  if(scroll)setTimeout(function(){{scroll.scrollTop=scroll.scrollHeight;}},30);
}}

(async function init(){{
  if(chatHistory.length===0){{
    try{{
      var r=await fetch(BACKEND+'/api/users/'+USER_ID+'/conversation-starter');
      var d=await r.json();
      if(d.message){{
        chatHistory=[{{role:'assistant',content:d.message}}];
        localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
      }}
    }}catch(e){{}}
  }}
  renderMessages();
  renderRecents();
}})();

function showTypingIndicator(){{
  var container=document.getElementById('hp-chat-messages');
  if(!container)return;
  var wrap=document.createElement('div');
  wrap.id='hp-typing';
  wrap.className='flex items-start gap-3 mb-4';
  wrap.innerHTML='<div style="width:32px;height:32px;border-radius:50%;overflow:hidden;flex-shrink:0;"><img src="{_MASCOT_DATA_URI}" style="width:100%;height:100%;object-fit:cover;"></div>'
    +'<div style="padding:12px 16px;border-radius:12px;background:#F7F7F7;border:1px solid #DDDDDD;display:flex;align-items:center;gap:4px;">'
    +'<span style="width:7px;height:7px;border-radius:50%;background:#AAAAAA;display:inline-block;animation:_typing 1s infinite ease-in-out;"></span>'
    +'<span style="width:7px;height:7px;border-radius:50%;background:#AAAAAA;display:inline-block;animation:_typing 1s infinite ease-in-out 0.2s;"></span>'
    +'<span style="width:7px;height:7px;border-radius:50%;background:#AAAAAA;display:inline-block;animation:_typing 1s infinite ease-in-out 0.4s;"></span>'
    +'</div>';
  container.appendChild(wrap);
  var scroll=document.getElementById('hp-chat-scroll');
  if(scroll)setTimeout(function(){{scroll.scrollTop=scroll.scrollHeight;}},30);
}}

function hideTypingIndicator(){{
  var el=document.getElementById('hp-typing');
  if(el)el.remove();
}}

async function sendChatMessage(){{
  if(_chatSending)return;
  var inp=document.getElementById('hp-chat-input');
  var msg=inp?inp.value.trim():'';
  if(!msg)return;
  _chatSending=true;
  inp.setAttribute('readonly','');
  inp.value='';
  inp.dispatchEvent(new Event('input',{{bubbles:true}}));
  (function(_i){{
    setTimeout(function(){{
      _i.value='';
      _i.dispatchEvent(new Event('input',{{bubbles:true}}));
      _i.removeAttribute('readonly');
      setTimeout(function(){{
        if(_i.value){{_i.value='';_i.dispatchEvent(new Event('input',{{bubbles:true}}));}}
      }},30);
    }},20);
  }})(inp);
  var sb=document.getElementById('hp-send-btn');
  if(sb)sb.disabled=true;
  _activeSessionId=null; // user sent a new message — conversation is now distinct from any loaded session
  chatHistory.push({{role:'user',content:msg}});
  localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
  renderMessages();
  renderRecents();
  showTypingIndicator();
  try{{
    var _hist=chatHistory.slice(0,-1).slice(-20); // everything before the current user message, capped at 20
    var r=await fetch(BACKEND+'/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{user_id:USER_ID,message:msg,conversation_history:_hist}})}});
    var d=await r.json();
    chatHistory.push({{role:'assistant',content:d.response||'Sorry, could not process that.'}});
    refreshForYouPanel();
    if(d.activity_created){{
      hideTypingIndicator();
      localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
      renderMessages();
      var _atype=d.activity_type||'';
      var _aemoji=_fyEmoji(_atype);
      var _acolor=_fyColor(_atype)||'#FF385C';
      setTimeout(function(){{_flyToDiscover(_aemoji,_acolor);}},400);
    }}
  }}catch(e){{chatHistory.push({{role:'assistant',content:'Connection error. Please try again.'}});}}
  if(!d||!d.activity_created){{
    hideTypingIndicator();
    localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
    renderMessages();
  }}
  if(sb)sb.disabled=false;
  _chatSending=false;
}}

var _sb=document.getElementById('hp-send-btn');
if(_sb)_sb.addEventListener('click',sendChatMessage);
var _ci=document.getElementById('hp-chat-input');
if(_ci)_ci.addEventListener('keydown',function(e){{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();sendChatMessage();}}}});


// ── Join activity (does cause Streamlit rerun to refresh recs) ────────────
function joinActivity(actId){{Streamlit.setComponentValue({{action:'join',activity_id:actId}});}}
function joinGymClass(gcId){{Streamlit.setComponentValue({{action:'join_gym',gym_class_id:gcId}});}}
function deleteActivity(actId,btn){{
  var card=btn.closest('[data-source]');
  if(!card)return;
  card.style.opacity='0.4';card.style.pointerEvents='none';
  fetch(BACKEND+'/api/activities/'+actId+'?user_id={user_id}',{{method:'DELETE'}})
    .then(function(r){{
      if(r.ok){{card.remove();}}
      else{{card.style.opacity='';card.style.pointerEvents='';}}
    }})
    .catch(function(){{card.style.opacity='';card.style.pointerEvents='';}});
}}

// Refresh For You panel on page load so cards reflect current state,
// not the server-side snapshot baked in at Streamlit render time.
loadProfileRecsForYouPanel();

// ── Activity-created fly animation ────────────────────────────────────────
function _flyToDiscover(emoji, color){{
  var chatScroll=document.getElementById('hp-chat-scroll');
  var navSpan=document.getElementById('nav-discover');
  if(!navSpan||!chatScroll)return;
  var navLink=navSpan.closest('a');
  if(!navLink)return;

  var bubbles=chatScroll.querySelectorAll('.flex.items-start');
  var originEl=bubbles.length?bubbles[bubbles.length-1]:chatScroll;
  var oR=originEl.getBoundingClientRect();
  var tR=navLink.getBoundingClientRect();

  var ox=oR.left+oR.width*0.5;
  var oy=oR.top+oR.height*0.5;
  var tx=tR.left+tR.width*0.5;
  var ty=tR.top+tR.height*0.5;
  var dx=tx-ox, dy=ty-oy;
  var mx=dx*0.45, my=dy*0.45-Math.abs(dx)*0.4;

  // Main particle: the activity emoji, large → shrinks into the nav
  (function(){{
    var uid='_fly_main_'+Date.now();
    var sEl=document.createElement('style');
    sEl.textContent='@keyframes '+uid+'{{'
      +'0%{{transform:translate(0,0) scale(1.1);opacity:1;}}'
      +'40%{{transform:translate('+mx+'px,'+my+'px) scale(1.4);opacity:1;}}'
      +'100%{{transform:translate('+dx+'px,'+dy+'px) scale(0.15);opacity:0;}}}}';
    document.head.appendChild(sEl);
    var fly=document.createElement('div');
    fly.textContent=emoji;
    fly.style.cssText='position:fixed;z-index:9999;font-size:36px;pointer-events:none;line-height:1;'
      +'left:'+(ox-18)+'px;top:'+(oy-18)+'px;'
      +'filter:drop-shadow(0 4px 12px '+color+'99);'
      +'animation:'+uid+' 0.75s cubic-bezier(0.4,0,0.2,1) forwards;';
    document.body.appendChild(fly);
    setTimeout(function(){{
      fly.remove();sEl.remove();
      // Bounce the nav icon when main particle lands
      navLink.style.transition='transform 0.3s cubic-bezier(0.34,1.56,0.64,1)';
      navLink.style.transform='scale(1.5)';
      setTimeout(function(){{navLink.style.transform='scale(1)';}},300);
    }},760);
  }})();

  // Two trailing sparkles — smaller, offset slightly, staggered
  [['✨',100,10],['⚡',180,-10]].forEach(function(s,i){{
    setTimeout(function(){{
      var uid2='_fly_s_'+Date.now()+'_'+i;
      var ox2=ox+s[2], oy2=oy+s[2];
      var dx2=tx-ox2, dy2=ty-oy2;
      var mx2=dx2*0.45, my2=dy2*0.45-Math.abs(dx2)*0.3;
      var sEl2=document.createElement('style');
      sEl2.textContent='@keyframes '+uid2+'{{'
        +'0%{{transform:translate(0,0) scale(0.8);opacity:0.9;}}'
        +'45%{{transform:translate('+mx2+'px,'+my2+'px) scale(1);opacity:0.8;}}'
        +'100%{{transform:translate('+dx2+'px,'+dy2+'px) scale(0.1);opacity:0;}}}}';
      document.head.appendChild(sEl2);
      var fly2=document.createElement('div');
      fly2.textContent=s[0];
      fly2.style.cssText='position:fixed;z-index:9998;font-size:18px;pointer-events:none;line-height:1;'
        +'left:'+(ox2-9)+'px;top:'+(oy2-9)+'px;'
        +'animation:'+uid2+' 0.65s cubic-bezier(0.4,0,0.2,1) forwards;';
      document.body.appendChild(fly2);
      setTimeout(function(){{fly2.remove();sEl2.remove();}},680);
    }},s[1]);
  }});
}}

// ── For-You panel helpers ──────────────────────────────────────────────────
var _FY_EMOJI={{football:'⚽',badminton:'🏸',basketball:'🏀',swimming:'🏊',yoga:'🧘',running:'🏃',gym:'💪',tennis:'🎾','board games':'🎲','board game':'🎲','coffee chat':'☕',coffee:'☕',ai:'🤖',english:'📚',movies:'🎬',karaoke:'🎤',dining:'🍽️',hiking:'🥾',boxing:'🥊',taekwondo:'🥋','book club':'📖',book:'📚',reading:'📚',workshop:'📚','knowledge-sharing':'💡',knowledge:'💡',product:'📦',pickleball:'🏓',zumba:'💃'}};
var _FY_COLOR={{football:'#00A699',badminton:'#FC642D',swimming:'#007A87',yoga:'#914669',running:'#FC642D',gym:'#FC642D','board games':'#FFB400','board game':'#FFB400','coffee chat':'#8B4513',coffee:'#8B4513',ai:'#4C6EF5',english:'#20C997'}};
function _fyEmoji(t){{var k=t.toLowerCase();for(var e in _FY_EMOJI){{if(k.indexOf(e)>=0)return _FY_EMOJI[e];}}return'🎯';}}
function _fyColor(t){{var k=t.toLowerCase();for(var e in _FY_COLOR){{if(k.indexOf(e)>=0)return _FY_COLOR[e];}}return'#5f5e5e';}}
function _fyEsc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}

// Shared card renderer for the For-You panel.
// items: array of {{id, title, activity_type, start_time, location, host_name, spots_left, is_joined, ai_insight}}
function _renderFyCards(items){{
  var c=document.getElementById('fy-cards');
  if(!c)return;

  function _doRender(){{
    if(!items||!items.length){{
      c.innerHTML='<div class="flex flex-col items-center justify-center h-32 text-center">'
        +'<div style="font-size:2.5rem;margin-bottom:8px;">🎯</div>'
        +'<p class="font-body-sm text-body-sm text-secondary">No recommendations yet.<br>Try exploring more activities!</p></div>';
      c.style.opacity='1';
      return;
    }}
    var html='';
    items.forEach(function(item){{
      var em=_fyEmoji(item.activity_type||'');
      var col=_fyColor(item.activity_type||'');
      var typeLabel=(item.activity_type||'activity').replace(/_/g,' ');
      typeLabel=typeLabel.charAt(0).toUpperCase()+typeLabel.slice(1);
      var badge='<div class="absolute top-3 left-3 bg-white px-3 py-1 rounded-full flex items-center space-x-1 shadow-sm">'
        +'<span class="material-symbols-outlined" style="font-size:14px;color:#FF385C;font-variation-settings:&quot;FILL&quot; 1;">bolt</span>'
        +'<span style="font-size:12px;font-weight:600;color:#FF385C">'+_fyEsc(typeLabel)+'</span></div>';
      var btn=item.is_joined
        ?'<button disabled class="w-full py-3 rounded-lg cursor-default" style="background:#EDFAF3;color:#1A7A4A;border:1px solid #B8EDD3;font-size:14px;font-weight:600;">✓ Joined</button>'
        :(item.spots_left>0
          ?'<button onclick="joinActivity('+item.id+')" class="w-full py-3 bg-rausch text-white rounded-lg hover:bg-rausch-active transition-all" style="font-size:14px;font-weight:600;">Join Activity</button>'
          :'<button disabled class="w-full py-3 rounded-lg cursor-default" style="background:#EFEDED;color:#5f5e5e;font-size:14px;font-weight:600;">Full</button>');
      html+='<div class="bg-canvas border border-hairline rounded-xl overflow-hidden group transition-all duration-300 p-4 space-y-4"'
        +' style="opacity:0;transform:translateY(16px)">'
        +'<div class="relative h-48 rounded-lg overflow-hidden flex items-center justify-center" style="background:linear-gradient(135deg,'+col+'33,'+col+'15);">'
        +'<span style="font-size:4rem;">'+em+'</span>'+badge+'</div>'
        +'<div class="space-y-1">'
        +'<h3 style="font-size:18px;font-weight:700;color:#222222;margin:0">'+_fyEsc(item.title)+'</h3>'
        +(item.ai_insight?'<p style="font-size:12px;color:#FF385C;margin:2px 0 0;font-style:italic">'+_fyEsc(item.ai_insight)+'</p>':'')
        +(item.start_time?'<p style="font-size:13px;color:#5f5e5e;margin:2px 0 0">'+_fyEsc(item.start_time)+'</p>':'')
        +(item.location?'<p style="font-size:13px;color:#5f5e5e;margin:0;text-transform:capitalize">'+_fyEsc(item.location)+'</p>':'')
        +(item.host_name?'<p style="font-size:13px;color:#5f5e5e;margin:0">Host: '+_fyEsc(item.host_name)+'</p>':'')
        +'<p style="font-size:12px;color:#5f5e5e;margin:4px 0 0">'+(item.spots_left>0?item.spots_left+' spot'+(item.spots_left>1?'s':'')+ ' left':'Full')+'</p>'
        +'</div>'+btn+'</div>';
    }});
    c.innerHTML=html;
    c.style.transform='';
    c.style.opacity='1';
    // Stagger: each card pops in with a spring bounce (scale + slide + fade)
    var cards=c.querySelectorAll(':scope > div');
    cards.forEach(function(card,i){{
      card.style.transition='none';
      card.style.opacity='0';
      card.style.transform='translateY(28px) scale(0.88)';
      setTimeout(function(){{
        card.style.transition='opacity 0.5s cubic-bezier(0.34,1.56,0.64,1), transform 0.5s cubic-bezier(0.34,1.56,0.64,1)';
        card.style.opacity='1';
        card.style.transform='translateY(0) scale(1)';
      }}, 40 + i*75);
    }});
  }}

  // Shrink + fade out, then spring cards in
  c.style.transition='opacity 0.15s ease, transform 0.15s ease';
  c.style.opacity='0';
  c.style.transform='scale(0.97)';
  setTimeout(_doRender, 160);
}}

// Load profile-based recommendations (no conversation context).
// Uses existing scoring: interests + participation history + social.
function loadProfileRecsForYouPanel(){{
  fetch(BACKEND+'/api/users/'+USER_ID+'/recommendations?limit=7')
    .then(function(r){{return r.json();}})
    .then(function(recs){{
      if(!recs||!recs.length)return;
      var items=recs.map(function(rec){{
        var act=rec.activity||{{}};
        var st=act.start_time||'';
        try{{
          var d=new Date(st);
          if(!isNaN(d.getTime())){{
            st=d.toLocaleDateString('en-US',{{weekday:'short',month:'short',day:'numeric'}})+' · '
              +d.toLocaleTimeString('en-US',{{hour:'2-digit',minute:'2-digit',hour12:false}});
            var et=act.end_time||'';
            if(et){{
              var de=new Date(et);
              if(!isNaN(de.getTime())){{
                st+='–'+de.toLocaleTimeString('en-US',{{hour:'2-digit',minute:'2-digit',hour12:false}});
              }}
            }}
          }}
        }}catch(e){{}}
        return{{id:act.id,title:act.title||'',activity_type:act.activity_type||'',
          start_time:st,location:act.location||'',host_name:act.host_name||'',
          spots_left:rec.spots_left||0,is_joined:rec.is_joined||false,
          ai_insight:rec.ai_insight||''}};
      }});
      _renderFyCards(items);
    }}).catch(function(){{}});
}}

// Refresh panel only when the agent actually recommended activities this session.
// If agent just chatted (no new RecommendationLog entries), panel stays unchanged.
function refreshForYouPanel(){{
  fetch(BACKEND+'/api/users/'+USER_ID+'/recent-shown-activities')
    .then(function(r){{return r.json();}})
    .then(function(items){{
      if(!items||!items.length)return; // agent didn't recommend — leave panel as-is
      _renderFyCards(items.map(function(item){{
        return{{id:item.id,title:item.title,activity_type:item.activity_type,
          start_time:item.start_time,location:item.location,host_name:item.host_name,
          spots_left:item.spots_left,is_joined:item.is_joined,ai_insight:''}};
      }}));
    }}).catch(function(){{}});
}}

// ── Browse filter tabs ─────────────────────────────────────────────────────
function filterBrowse(type){{
  document.querySelectorAll('#browse-grid>div').forEach(function(c){{
    var lt=c.getAttribute('data-location-type');
    if(type==='all')c.style.display='';
    else if(type==='on_campus')c.style.display=(lt==='on_campus')?'':'none';
    else c.style.display=(lt==='off_campus')?'':'none';
  }});
  ['filter-all','filter-on','filter-off'].forEach(function(id){{
    var el=document.getElementById(id);
    if(el){{el.style.background='#fff';el.style.color='#5f5e5e';el.style.border='1px solid #ddd';}}
  }});
  var ids={{all:'filter-all',on_campus:'filter-on',off_campus:'filter-off'}};
  var el=document.getElementById(ids[type]);
  if(el){{el.style.background='#222';el.style.color='#fff';el.style.border='2px solid #222';}}
}}

// ── Discover: live refresh ─────────────────────────────────────────────────
var _DSC_COLORS={{'gym':'#FF385C','yoga':'#558B2F','zumba':'#C2185B','boxing':'#B71C1C',
  'swimming':'#0288D1','football':'#FF6B35','pickleball':'#7742AA','badminton':'#7742AA',
  'running':'#1A7A4A','taekwondo':'#5D4037','board games':'#B7691B','movies':'#455A64',
  'dining':'#E65100','esports':'#1565C0','coffee chat':'#6D4C41','coffee':'#6D4C41',
  'karaoke':'#AD1457','picnics':'#558B2F','concerts':'#6A1B9A','ai':'#1D6FA4',
  'product':'#2E7D32','english':'#0277BD','book club':'#4527A0','knowledge-sharing':'#00695C'}};
var _DSC_EMOJI={{'gym':'🏋️','yoga':'🧘','zumba':'💃','boxing':'🥊','swimming':'🏊',
  'football':'⚽','pickleball':'🏓','badminton':'🏸','running':'🏃','taekwondo':'🥋',
  'board games':'🎲','movies':'🎬','dining':'🍽️','esports':'🎮','coffee chat':'☕','coffee':'☕',
  'karaoke':'🎤','picnics':'🧺','concerts':'🎵','ai':'🤖','product':'📦',
  'english':'📚','book club':'📖','knowledge-sharing':'💡',
  'book':'📚','reading':'📚','workshop':'📚','hiking':'🥾'}};
var _DSC_DIFF_CFG={{
  'Beginner':    {{bg:'#E8F5E9',tc:'#2E7D32',ic:'signal_cellular_1_bar'}},
  'Intermediate':{{bg:'#FFF8E1',tc:'#F57F17',ic:'signal_cellular_2_bar'}},
  'Advanced':    {{bg:'#FCE4EC',tc:'#C62828',ic:'signal_cellular_4_bar'}},
  'All Levels':  {{bg:'#F3E5F5',tc:'#6A1B9A',ic:'signal_cellular_alt'}}
}};

function _dscBadge(diff){{
  var d=_DSC_DIFF_CFG[diff];if(!d)return'';
  return '<div style="position:absolute;top:12px;left:12px;padding:3px 10px;border-radius:999px;display:inline-flex;align-items:center;gap:4px;background:'+d.bg+'">'+
    '<span class="material-symbols-outlined" style="font-size:13px;color:'+d.tc+'">'+d.ic+'</span>'+
    '<span style="font-size:11px;font-weight:700;color:'+d.tc+'">'+diff+'</span></div>';
}}

function _dscCard(item){{
  var src=item.source||'user_created';
  var lt=item.location_type||'off_campus';
  var atype=(item.activity_type||'other').toLowerCase();
  var color=_DSC_COLORS[atype]||'#5f5e5e';
  var em=_DSC_EMOJI[atype]||'🎯';
  var title=(item.title||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  var loc=(item.location||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  var host=(item.host_name||(src==='platform'?'Platform':'')).replace(/&/g,'&amp;').replace(/</g,'&lt;');
  var st=item.start_time||'';var et=item.end_time||'';
  var timeLabel=st+(et?'–'+et:'');
  var spots=item.spots_left||0;
  var joined=!!item.is_joined;
  var isFree=!!item.is_free_facility;
  var actId=item.id||0;
  var diff=item.difficulty||'';
  var badge=diff?_dscBadge(diff):'';
  var delBtn='';
  if(src==='user_created'&&item.created_by===USER_ID){{
    delBtn='<button onclick="event.stopPropagation();deleteActivity('+actId+',this)" title="Delete" style="position:absolute;top:10px;right:10px;width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.9);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,0.15)"><span class="material-symbols-outlined" style="font-size:16px;color:#c0392b">delete</span></button>';
  }}
  var btnBase='width:100%;height:44px;border-radius:8px;font-size:14px;font-weight:600;border:none;box-sizing:border-box;cursor:';
  var btnHtml='';
  if(isFree){{
    btnHtml='<div style="'+btnBase+'default;background:#F7F7F7;color:#5f5e5e;display:flex;align-items:center;justify-content:center;gap:6px;border-radius:8px"><span class="material-symbols-outlined" style="font-size:18px">door_open</span>Walk-in · Miễn phí</div>';
  }}else if(joined){{
    btnHtml='<button disabled style="'+btnBase+'default;background:#EDFAF3;color:#1A7A4A;">✓ Joined</button>';
  }}else if(spots>0){{
    var fn=src==='platform'?'joinGymClass':'joinActivity';
    var lbl=src==='platform'?'Join':'Join Activity';
    btnHtml='<button onclick="'+fn+'('+actId+')" style="'+btnBase+'pointer;background:#FF385C;color:#fff;">'+lbl+'</button>';
  }}else{{
    btnHtml='<button disabled style="'+btnBase+'default;background:#EFEDED;color:#5f5e5e;">Full</button>';
  }}
  return '<div class="bg-canvas border border-hairline rounded-xl overflow-hidden transition-all duration-300 p-4 space-y-4" data-source="'+src+'" data-location-type="'+lt+'">'+
    '<div class="relative h-40 rounded-lg overflow-hidden flex items-center justify-center" style="background:linear-gradient(135deg,'+color+'33,'+color+'15)">'+
    '<span style="font-size:3.5rem">'+em+'</span>'+badge+delBtn+'</div>'+
    '<div class="space-y-1"><h3 style="font-size:16px;font-weight:700;color:#222222;margin:0">'+title+'</h3>'+
    (timeLabel?'<div style="font-size:13px;color:#5f5e5e">'+timeLabel+'</div>':'')+
    (loc?'<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:13px"><span class="material-symbols-outlined" style="font-size:16px">location_on</span><span style="text-transform:capitalize">'+loc+'</span></div>':'')+
    (host?'<div class="flex items-center space-x-1" style="color:#5f5e5e;font-size:13px"><span class="material-symbols-outlined" style="font-size:16px">person</span><span>'+host+'</span></div>':'')+
    '</div>'+btnHtml+'</div>';
}}

function renderBrowseGrid(items){{
  var grid=document.getElementById('browse-grid');
  if(!grid)return;
  if(!items||!items.length){{
    grid.innerHTML='<div class="flex flex-col items-center justify-center h-48 text-center"><div style="font-size:2.5rem;margin-bottom:8px;">🔍</div><p style="font-size:14px;color:#5f5e5e">No activities found.</p></div>';
    return;
  }}
  // Sort by start time ascending; joined activities float to top within their time group
  items.sort(function(a,b){{
    if(a.is_joined&&!b.is_joined)return -1;
    if(!a.is_joined&&b.is_joined)return 1;
    return (a.sort_ts||0)-(b.sort_ts||0);
  }});
  grid.innerHTML=items.map(_dscCard).join('');
  filterBrowse('all');
}}

var _dscRefreshing=false;
function refreshBrowseGrid(force){{
  if(_dscRefreshing&&!force)return;
  _dscRefreshing=true;
  var grid=document.getElementById('browse-grid');
  if(grid)grid.style.opacity='0.5';
  fetch(BACKEND+'/api/activities/browse?user_id='+USER_ID)
    .then(function(r){{return r.json();}})
    .then(function(data){{
      renderBrowseGrid(data);
      if(grid)grid.style.opacity='';
    }})
    .catch(function(){{if(grid)grid.style.opacity='';}})
    .finally(function(){{_dscRefreshing=false;}});
}}

// ── Chat sessions (New Chat + Recents) ────────────────────────────────────
function getSessions(){{
  try{{return JSON.parse(localStorage.getItem(SESSIONS_KEY)||'[]');}}catch(e){{return[];}}
}}

function saveCurrentSession(){{
  var userMsgs=chatHistory.filter(function(m){{return m.role==='user';}});
  if(!userMsgs.length)return;
  if(_activeSessionId!==null)return; // loaded from recents, not modified — already saved
  var sessions=getSessions();
  var title=userMsgs[0].content.slice(0,40);
  var _now=Date.now();
  sessions.unshift({{id:_now,title:title,messages:chatHistory.slice(),created_at:new Date().toISOString(),updated_at:_now}});
  if(sessions.length>15)sessions=sessions.slice(0,15);
  localStorage.setItem(SESSIONS_KEY,JSON.stringify(sessions));
}}

function renderRecents(){{
  var el=document.getElementById('recents-list');
  if(!el)return;
  var sessions=getSessions().slice().sort(function(a,b){{return (b.updated_at||b.id)-(a.updated_at||a.id);}});
  var items='';
  // Current active session — only show if it's a genuinely new unsaved conversation
  var userMsgs=chatHistory.filter(function(m){{return m.role==='user';}});
  if(userMsgs.length && _activeSessionId===null){{
    var curTitle=userMsgs[0].content.slice(0,40);
    items+='<a href="#" onclick="showView(`agent`);return false;"'
      +' style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#E00B41;font-weight:600;background:#FFF0EE;border-radius:8px;margin:0 -8px;padding:4px 8px;">'
      +'<span class="material-symbols-outlined" style="font-size:18px;flex-shrink:0;color:#E00B41">chat_bubble</span>'
      +'<span style="font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'+curTitle+'</span></a>';
  }}
  items+=sessions.map(function(s){{
    var isActive=s.id===_activeSessionId;
    var activeStyle=isActive
      ?'background:#FFF0EE;border-radius:8px;margin:0 -8px;padding:4px 8px;'
      :'padding:4px 0;';
    var linkColor=isActive?'#E00B41':'#717171';
    var iconColor=isActive?'color:#E00B41':'';
    return '<div style="display:flex;align-items:center;'+activeStyle+'"'
      +' onmouseenter="this.lastElementChild.style.opacity=1"'
      +' onmouseleave="this.lastElementChild.style.opacity=0">'
      +'<a href="#" onclick="loadSession('+s.id+');return false;"'
      +' style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;text-decoration:none;color:'+linkColor+';font-weight:'+(isActive?'600':'400')+'">'
      +'<span class="material-symbols-outlined" style="font-size:18px;flex-shrink:0;'+iconColor+'">chat_bubble</span>'
      +'<span style="font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'+s.title+'</span></a>'
      +'<button class="del-btn" onclick="event.stopPropagation();deleteSession('+s.id+')"'
      +' style="flex-shrink:0;width:20px;height:20px;border:none;background:none;cursor:pointer;opacity:0;padding:0;display:flex;align-items:center;justify-content:center;transition:opacity 0.15s"'
      +' title="Delete">'
      +'<span class="material-symbols-outlined" style="font-size:15px;color:#aaa">delete</span></button>'
      +'</div>';
  }}).join('');
  el.innerHTML=items||'<p style="font-size:12px;color:#aaa;padding:4px 0">No recent chats</p>';
}}

function _showMsgSkeleton(){{
  var container=document.getElementById('hp-chat-messages');
  if(!container)return;
  var welcome=document.getElementById('hp-welcome');
  if(welcome)welcome.style.display='none';
  var skels=[
    {{side:'left', lines:['100%','95%','88%','70%']}},
    {{side:'right', lines:['90%','72%']}},
    {{side:'left', lines:['100%','96%','80%']}},
    {{side:'right', lines:['95%','82%','60%']}},
    {{side:'left', lines:['100%','92%','78%','55%']}},
    {{side:'right', lines:['85%']}},
  ];
  container.innerHTML=skels.map(function(sk){{
    var isUser=sk.side==='right';
    var linesHtml=sk.lines.map(function(w){{
      return '<div class="skel-line" style="height:13px;width:'+w+';margin-bottom:6px"></div>';
    }}).join('');
    var bubble='<div style="width:'+(isUser?'55%':'75%')+';padding:14px 16px;border-radius:12px;background:'+(isUser?'#e8e8e8':'#f0f0f0')+'">'
      +linesHtml+'</div>';
    var avatar=isUser?'':'<div style="width:32px;height:32px;border-radius:50%;flex-shrink:0;" class="skel-line"></div>';
    return '<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:16px;'+(isUser?'flex-direction:row-reverse':'')+'">'
      +avatar+bubble+'</div>';
  }}).join('');
}}

function loadSession(sessionId){{
  saveCurrentSession();
  var sessions=getSessions();
  var s=sessions.find(function(x){{return x.id===sessionId;}});
  if(!s)return;
  // Bump updated_at so this session rises to the top on next render
  s.updated_at=Date.now();
  localStorage.setItem(SESSIONS_KEY,JSON.stringify(sessions));
  chatHistory=s.messages.slice();
  _activeSessionId=sessionId;
  localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
  var _inp=document.getElementById('hp-chat-input');if(_inp)_inp.value='';
  showView('agent');
  _showMsgSkeleton();
  renderRecents();
  setTimeout(function(){{renderMessages(true);}},380);
}}

function deleteSession(sessionId){{
  var sessions=getSessions().filter(function(x){{return x.id!==sessionId;}});
  localStorage.setItem(SESSIONS_KEY,JSON.stringify(sessions));
  renderRecents();
}}

function newChat(){{
  _chatSending=false;
  saveCurrentSession();
  chatHistory=[];
  _activeSessionId=null;
  localStorage.removeItem(CHAT_KEY);
  var _inp=document.getElementById('hp-chat-input');if(_inp)_inp.value='';
  renderMessages();
  renderRecents();
  loadProfileRecsForYouPanel();
  showView('agent');
  fetch(BACKEND+'/api/users/{user_id}/conversation-starter')
    .then(function(r){{return r.json();}})
    .then(function(d){{
      if(d.message){{
        chatHistory=[{{role:'assistant',content:d.message}}];
        localStorage.setItem(CHAT_KEY,JSON.stringify(chatHistory));
        renderMessages();
      }}
    }}).catch(function(){{}});
}}

// ── Profile: interests modal ───────────────────────────────────────────────
function showInterestModal(){{var m=document.getElementById('interest-modal');if(m)m.style.display='flex';}}
function hideInterestModal(){{var m=document.getElementById('interest-modal');if(m)m.style.display='none';}}
function saveInterests(){{
  var sel=[];
  document.querySelectorAll('.pf-int-cb:checked').forEach(function(cb){{sel.push(cb.value);}});
  Streamlit.setComponentValue({{action:'update_interests',interests:sel}});
  hideInterestModal();
}}
(function(){{var m=document.getElementById('interest-modal');if(m)m.addEventListener('click',function(e){{if(e.target===this)hideInterestModal();}});}})();
</script>"""
    html = re.sub(r"<script>.*?</script>\s*(?=</body>)", new_script + "\n", html, flags=re.DOTALL)
    return html


def _build_discover_cards_html(recommendations: list) -> str:
    if not recommendations:
        return (
            '<div class="col-span-full text-center py-20 text-secondary">'
            '<div style="font-size:3rem;margin-bottom:12px;">🎯</div>'
            '<p class="font-display-md text-display-md text-ink">No activities yet</p>'
            '<p class="font-body-sm text-body-sm text-secondary mt-2">Be the first to create one!</p>'
            "</div>"
        )
    cards = []
    for rec in recommendations:
        act = rec.get("activity", {})
        act_id = act.get("id", 0)
        title = _escape_html(act.get("title", ""))
        atype = act.get("activity_type", "other").lower()
        color = _HP_TYPE_COLORS.get(atype, "#5f5e5e")
        emoji = _HP_EMOJI_MAP.get(atype, "🎯")
        match_score = rec.get("match_score", 0)
        ai_insight = _escape_html(rec.get("ai_insight", ""))
        spots_left = rec.get("spots_left", 0)
        is_joined = rec.get("is_joined", False)
        current = act.get("current_participants", 0)
        limit = act.get("participant_limit", 0)
        location = _escape_html(act.get("location", ""))
        difficulty = act.get("difficulty") or ""
        try:
            _sd = datetime.fromisoformat(act.get("start_time", ""))
            _et_raw2 = act.get("end_time") or ""
            _end_suffix2 = ""
            if _et_raw2:
                try:
                    _end_suffix2 = "–" + datetime.fromisoformat(_et_raw2).strftime("%H:%M")
                except Exception:
                    pass
            time_str = _sd.strftime("%a, %b %d · %H:%M") + _end_suffix2
        except Exception:
            time_str = ""

        tl_badge = _difficulty_badge(difficulty) if difficulty else (
            f'<div class="absolute top-3 left-3 px-3 py-1 bg-white border border-hairline rounded-full flex items-center gap-1 shadow-sm">'
            f'<span class="text-rausch font-bold text-[13px]">{match_score}% Match</span>'
            f'</div>'
        )

        if is_joined:
            tr_badge = '<div class="absolute top-3 right-3 px-3 py-1 rounded-full flex items-center gap-1" style="background:#EDFAF3;border:1px solid #B8EDD3"><span class="font-bold text-[13px]" style="color:#1A7A4A">✓ Joined</span></div>'
        elif spots_left <= 2 and spots_left > 0:
            tr_badge = f'<div class="absolute top-3 right-3 px-3 py-1 rounded-full" style="background:#FFF3E0;border:1px solid #FFCC80"><span class="font-bold text-[13px]" style="color:#E65100">{spots_left} left</span></div>'
        else:
            tr_badge = ""

        if is_joined:
            join_html = '<span class="font-body-sm text-body-sm font-semibold" style="color:#1A7A4A">✓ You\'re in</span>'
        elif spots_left > 0:
            join_html = f'<button onclick="event.stopPropagation();joinActivity({act_id})" class="font-body-sm text-body-sm font-semibold hover:underline" style="color:#FF385C">Join →</button>'
        else:
            join_html = '<span class="font-body-sm text-body-sm text-secondary">Full</span>'

        onclick_attr = "" if (is_joined or spots_left == 0) else f'onclick="joinActivity({act_id})"'
        cards.append(
            f'<div class="group cursor-pointer" {onclick_attr}>'
            f'<div class="relative rounded-xl overflow-hidden mb-3 flex items-center justify-center" style="aspect-ratio:1;background:linear-gradient(135deg,{color}25,{color}10);">'
            f'<span style="font-size:4rem;">{emoji}</span>'
            f"{tl_badge}"
            f"{tr_badge}"
            f"</div>"
            f'<div class="flex justify-between items-start">'
            f'<h3 class="font-display-md text-display-md text-ink group-hover:underline">{title}</h3>'
            f'<div class="flex items-center gap-1 text-secondary ml-2 flex-shrink-0">'
            f'<span class="material-symbols-outlined" style="font-size:14px">group</span>'
            f'<span style="font-size:12px">{current}/{limit}</span>'
            f"</div>"
            f"</div>"
            f'<p class="font-body-sm text-body-sm text-secondary"><span style="text-transform:capitalize">{location}</span> &middot; {time_str}</p>'
            f'<p class="font-body-sm text-body-sm text-secondary" style="margin-top:4px;font-style:italic;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">{ai_insight}</p>'
            f'<div style="margin-top:8px">{join_html}</div>'
            f"</div>"
        )
    return "\n".join(cards)


def _build_create_html(user_name: str, user_id: int = 0, error_msg: str = "") -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/create_your_activity_afterwork_agent/code.html")) as f:
        html = f.read()
    html = _fix_mascot(html)

    # ── Fixed layout: sidebar fixed, main scrolls ─────────────────────────────
    html = html.replace("</style>",
        """html,body{height:100%;overflow:hidden;margin:0;padding:0;}
        main.ml-64{height:100%;overflow-y:auto;}
        </style>""", 1)

    # ── Personalise sidebar greeting ──────────────────────────────────────────
    html = html.replace("Need help, Alex?", f"Need help, {user_name}?")

    # ── Wire nav links ────────────────────────────────────────────────────────
    html = html.replace(
        '<span class="font-nav-link text-nav-link">Discover</span>',
        '<span id="nav-discover" class="font-nav-link text-nav-link">Discover</span>',
    )
    html = html.replace(
        '<span class="font-nav-link text-nav-link">My Agent</span>',
        '<span id="nav-agent" class="font-nav-link text-nav-link">My Agent</span>',
    )
    html = html.replace(
        '<span class="font-nav-link text-nav-link">Profile</span>',
        '<span id="nav-profile" class="font-nav-link text-nav-link">Profile</span>',
    )

    # ── Pre-fill today's date ─────────────────────────────────────────────────
    _today = date.today().isoformat()
    html = html.replace('type="date">', f'type="date" id="ca-date" value="{_today}">', 1)
    html = html.replace(
        'type="time">\n<span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-secondary text-[20px]">schedule</span>',
        'type="time" id="ca-start" value="18:00">\n<span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-secondary text-[20px]">schedule</span>',
        1,
    )
    html = html.replace(
        'type="time">\n<span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-secondary text-[20px]">more_time</span>',
        'type="time" id="ca-end" value="19:00">\n<span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-secondary text-[20px]">more_time</span>',
        1,
    )

    # ── Error banner ──────────────────────────────────────────────────────────
    if error_msg:
        _banner = (
            f'<div style="background:#FEE2E2;border:1px solid #EF4444;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:20px;color:#B91C1C;font-size:14px;">'
            f'{error_msg}</div>\n'
        )
        html = html.replace(
            '<section class="bg-canvas border border-hairline rounded-xl p-8 lg:p-12">',
            _banner + '<section class="bg-canvas border border-hairline rounded-xl p-8 lg:p-12">',
        )

    # ── Streamlit bridge + interactivity ──────────────────────────────────────
    _script = f"""<script>
var Streamlit={{
  setComponentReady:function(){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1}},'*');}},
  setComponentValue:function(v){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:v}},'*');}},
  setFrameHeight:function(h){{window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h}},'*');}}
}};
Streamlit.setComponentReady();
(function(){{try{{var pd=window.parent.document;if(!pd.getElementById('_alp_chrome_css')){{var cs=pd.createElement('style');cs.id='_alp_chrome_css';cs.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{{display:none!important}}.main .block-container{{padding:0!important;max-width:100%!important}}[data-testid="stApp"],.stApp{{background:#FFF5F0!important}}';pd.head.appendChild(cs);}}}}catch(e){{}}}})();
Streamlit.setFrameHeight(window.parent.innerHeight);
var BACKEND='{_BACKEND_URL}';
var USER_ID={user_id};

// Nav
var _nd=document.getElementById('nav-discover');
if(_nd)_nd.closest('a').addEventListener('click',function(e){{e.preventDefault();Streamlit.setComponentValue({{action:'navigate',page:'browse'}});}});
var _na=document.getElementById('nav-agent');
if(_na)_na.closest('a').addEventListener('click',function(e){{e.preventDefault();Streamlit.setComponentValue({{action:'navigate',page:'discover'}});}});
var _np=document.getElementById('nav-profile');
if(_np)_np.closest('a').addEventListener('click',function(e){{e.preventDefault();Streamlit.setComponentValue({{action:'navigate',page:'profile'}});}});

// Difficulty level toggle
var _selLevel='';
document.querySelectorAll('.flex.gap-2 button[type="button"]').forEach(function(btn){{
  btn.addEventListener('click',function(){{
    _selLevel=this.textContent.trim();
    document.querySelectorAll('.flex.gap-2 button[type="button"]').forEach(function(b){{
      b.className='px-4 py-2 border border-hairline rounded-full font-body-sm text-body-sm hover:border-ink transition-colors';
    }});
    this.className='px-4 py-2 border border-ink bg-ink text-canvas rounded-full font-body-sm text-body-sm';
  }});
}});

// Form submit → direct to backend API (no page reload)
var _TYPE_MAP={{
  'Gym':'gym','Yoga':'yoga','Zumba':'zumba','Pickleball':'pickleball',
  'Badminton':'badminton','Football':'football','Running':'running',
  'Board Games':'board games','Dining':'dining','Coffee Chat':'coffee',
  'Karaoke':'karaoke','Picnics':'picnic','AI':'ai','Product':'product',
  'Book Club':'book club','English':'english','Swimming':'swimming'
}};
var _crForm=document.querySelector('form');
if(_crForm)_crForm.addEventListener('submit',function(e){{
  e.preventDefault();
  var title=(document.getElementById('title')||{{}}).value||'';
  var type=(document.getElementById('type')||{{}}).value||'';
  var locType=(document.getElementById('location-type')||{{}}).value||'off_campus';
  var loc=locType==='on_campus'
    ? ((document.getElementById('location-select')||{{}}).value||'')
    : ((document.getElementById('location-input')||{{}}).value||'');
  var desc=(document.getElementById('description')||{{}}).value||'';
  var guide=(document.getElementById('guidelines')||{{}}).value||'';
  title=title.trim();loc=loc.trim();type=type.trim();
  if(!title||!loc||!type||type==='Choose Type'||loc==='Choose a campus venue'){{
    alert('Please fill in Activity Title, Activity Type, and Location.');return;
  }}
  var dateVal=(document.getElementById('ca-date')||{{}}).value||'';
  var startVal=(document.getElementById('ca-start')||{{}}).value||'18:00';
  var endVal=(document.getElementById('ca-end')||{{}}).value||'19:00';
  var grpEl=document.getElementById('participants');
  var grpText=grpEl?grpEl.value:'10 participants';
  var grpNum=grpText==='Unlimited'?100:(parseInt(grpText)||10);
  var actType=_TYPE_MAP[type]||type.toLowerCase();
  var btn=document.querySelector('button[type="submit"]');
  if(btn){{btn.innerHTML='<span class="material-symbols-outlined" style="vertical-align:middle">sync</span> Posting...';btn.disabled=true;}}
  fetch(BACKEND+'/api/activities?creator_id='+USER_ID,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{
      title:title,activity_type:actType,location:loc,location_type:locType,
      description:desc,guidelines:guide||null,start_time:dateVal+'T'+startVal+':00',end_time:dateVal+'T'+endVal+':00',
      participant_limit:grpNum,difficulty:_selLevel||null
    }})
  }}).then(function(r){{
    if(!r.ok)throw new Error('error');
    return r.json();
  }}).then(function(){{
    if(btn){{btn.innerHTML='<span class="material-symbols-outlined" style="vertical-align:middle">check_circle</span> Posted!';}}
    setTimeout(function(){{
      Streamlit.setComponentValue({{action:'navigate',page:'browse'}});
    }},1200);
  }}).catch(function(){{
    if(btn){{btn.innerHTML='Post Activity';btn.disabled=false;}}
    alert('Failed to post activity. Please try again.');
  }});
}});
</script>"""
    html = html.replace("</body>", _script + "\n</body>")
    return html


def _build_profile_html(user: dict) -> str:
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "design/my_profile_afterwork_agent/code.html")) as f:
        html = f.read()
    html = _fix_mascot(html)

    full_name = _escape_html(user.get("full_name") or user.get("domain", ""))
    domain = _escape_html(user.get("domain", ""))
    title_val = _escape_html(user.get("title") or "Employee")
    company = _escape_html(user.get("company") or "—")
    department = _escape_html(user.get("department") or "—")
    org_group = _escape_html(user.get("org_group") or "—")
    squad = _escape_html(user.get("squad") or "—")
    interests = user.get("interests", [])
    initial = (full_name[0] if full_name else "?").upper()

    # Profile strength
    pct = 50
    if user.get("full_name"): pct += 10
    if user.get("company"): pct += 5
    if user.get("department"): pct += 5
    if user.get("org_group"): pct += 5
    if interests: pct += 20
    pct = min(pct, 100)
    tip = "Add more interests and details to unlock better recommendations." if pct < 100 else "Your profile is looking great!"

    # Fixed layout
    html = html.replace("</style>",
        "html,body{height:100%;overflow:hidden;margin:0;padding:0;}"
        "main.flex-1.ml-64{height:100%;overflow-y:auto;}"
        "</style>", 1)

    # Replace avatar img with initial-based circle
    html = html.replace(
        '<img alt="Nguyen Thanh An Profile Avatar" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBmWfvsLyu_azF3tdLua1Ab-8Cdz8q371_ss07Y23Stqxq-TWSO5vWJhK2fSHIqPma-SEY8RzZuFqATQUxyTVYTCvNNzvUnueuKsORGER6qo0A_BSScZFnaycsOcDSv-guzq_p-yEhk0dxmSTspSBFiteryywLe8z1DSMp5r5v5vC8nYTgV8zMMel3RyWKSMe-gyANz5_NjHHt-NuQ0ty4WLe2C9zeecFaXN6kCZpWzNcn02scqhiOum3ztwUdHFHf_R5QBQjOAlFc">',
        f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#FF385C,#c90034);font-size:48px;font-weight:700;color:#fff;">{initial}</div>',
    )
    # Remove camera button (not functional yet)
    html = html.replace(
        '<button class="absolute bottom-0 right-0 p-2 bg-white border border-hairline rounded-full shadow-md hover:scale-110 transition-transform">\n<span class="material-symbols-outlined text-rausch text-[18px]">photo_camera</span>\n</button>', '')

    # Profile header - name and title
    html = html.replace(
        '<h2 class="font-display-xl text-display-xl text-ink">Nguyen Thanh An</h2>',
        f'<h2 class="font-display-xl text-display-xl text-ink">{full_name}</h2>',
    )
    html = html.replace(
        '<p class="font-body-md text-body-md text-secondary">Senior Software Engineer</p>',
        f'<p class="font-body-md text-body-md text-secondary">{title_val} · @{domain}</p>',
    )

    # Personal Details - Full Name field
    html = html.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Full Name</label>\n'
        '<p class="font-body-md text-body-md text-ink">Nguyen Thanh An</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Full Name</label>\n'
        f'<p class="font-body-md text-body-md text-ink">{full_name}</p>',
    )
    # Domain field
    html = html.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">domain</label>\n'
        '<p class="font-body-md text-body-md text-ink">annt7</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-2">Domain</label>\n'
        f'<p class="font-body-md text-body-md text-ink">@{domain}</p>',
    )
    # Birthdate & Horoscope (not in schema, show —)
    html = html.replace('>6 April 1995<', '>—<')
    html = html.replace('>Aries<', '>—<')

    # Work & Organization
    html = html.replace('>ZP<', f'>{company}<')
    html = html.replace('>&nbsp;N/A<', f'>&nbsp;{department}<')
    html = html.replace(
        '<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-3">Group</label>\n'
        '<p class="font-display-md text-display-md text-ink">N/A</p>',
        f'<label class="block font-caption text-caption text-secondary uppercase tracking-wider mb-3">Group</label>\n'
        f'<p class="font-display-md text-display-md text-ink">{org_group}</p>',
    )
    html = html.replace('>Consumer Solutions<', f'>{squad}<')

    # Interests pills
    _interest_icons = {
        "football": "sports_soccer", "running": "sprint", "gym": "fitness_center",
        "swimming": "pool", "taekwondo": "sports_martial_arts", "badminton": "sports_tennis",
        "ai": "smart_toy", "product": "inventory_2", "english": "translate",
        "movies": "movie", "board games": "casino", "coffee chat": "local_cafe",
        "karaoke": "mic", "yoga": "self_improvement", "zumba": "music_note",
        "pickleball": "sports_tennis", "dining": "restaurant", "picnic": "park",
        "photography": "photo_camera", "specialty coffee": "local_cafe",
        "book club": "menu_book",
    }
    pills_html = "".join([
        f'<span class="px-5 py-2.5 rounded-full border border-hairline bg-white hover:border-rausch hover:text-rausch cursor-pointer transition-all flex items-center gap-2">'
        f'<span class="material-symbols-outlined text-[18px]">{_interest_icons.get(i.lower(), "star")}</span>'
        f'{_escape_html(i.capitalize())}</span>'
        for i in interests
    ])
    pills_html += ('<button onclick="showInterestModal()" class="px-5 py-2.5 rounded-full border border-dashed'
                   ' border-secondary text-secondary hover:border-ink hover:text-ink flex items-center gap-2 transition-all">'
                   '<span class="material-symbols-outlined text-[18px]">add</span>Add New</button>')
    html = re.sub(
        r'<div class="flex flex-wrap gap-3">.*?</div>(?=\s*</section>)',
        f'<div class="flex flex-wrap gap-3">{pills_html}</div>',
        html, flags=re.DOTALL, count=1,
    )

    # Manage Interests button
    html = html.replace(
        '<button class="text-rausch font-button-md text-body-sm hover:underline">Manage Interests</button>',
        '<button onclick="showInterestModal()" class="text-rausch font-button-md text-body-sm hover:underline">Manage Interests</button>',
    )

    # Profile strength
    html = html.replace('<span class="font-nav-link text-ink">85%</span>', f'<span class="font-nav-link text-ink">{pct}%</span>')
    html = html.replace('style="width: 85%"', f'style="width:{pct}%"')
    html = html.replace(
        "<p class=\"mt-4 font-caption text-caption text-secondary\">Add a 'Personal Bio' to reach 100% and unlock more personalized agent recommendations.</p>",
        f'<p class="mt-4 font-caption text-caption text-secondary">{tip}</p>',
    )

    # Wire nav links
    html = html.replace('<span class="">Discover</span>', '<span id="nav-discover">Discover</span>')
    html = html.replace('<span class="">My Agent</span>', '<span id="nav-agent">My Agent</span>')
    html = html.replace('<span class="">Create Activity</span>', '<span id="nav-create">Create Activity</span>')

    # Interests modal
    _all_interests = [
        "football", "running", "gym", "swimming", "badminton", "ai", "product",
        "english", "movies", "board games", "coffee chat", "karaoke", "yoga",
        "zumba", "pickleball", "dining", "book club",
    ]
    _int_lower = [i.lower() for i in interests]
    _modal_checks = "".join([
        f'<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;cursor:pointer;">'
        f'<input type="checkbox" class="int-cb" value="{i}" {"checked" if i in _int_lower else ""}'
        f' style="accent-color:#FF385C;width:16px;height:16px;">'
        f'<span class="material-symbols-outlined" style="font-size:18px;color:#5f5e5e;">{_interest_icons.get(i, "star")}</span>'
        f'<span style="font-size:14px;color:#222;">{i.capitalize()}</span>'
        f'</label>'
        for i in _all_interests
    ])
    _modal_html = (
        '<div id="interest-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:9999;align-items:center;justify-content:center;">'
        '<div style="background:#fff;border-radius:16px;max-width:480px;width:90%;max-height:80vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.15);">'
        '<div style="padding:20px 24px;border-bottom:1px solid #DDDDDD;display:flex;justify-content:space-between;align-items:center;">'
        '<h3 style="font-size:18px;font-weight:600;color:#222;margin:0;">Manage Interests</h3>'
        '<button onclick="hideInterestModal()" style="background:none;border:none;cursor:pointer;font-size:22px;color:#5f5e5e;line-height:1;">✕</button>'
        '</div>'
        f'<div style="overflow-y:auto;padding:8px 12px;flex:1;display:grid;grid-template-columns:1fr 1fr;gap:2px;">{_modal_checks}</div>'
        '<div style="padding:16px 24px;border-top:1px solid #DDDDDD;">'
        '<button onclick="saveInterests()" style="background:#FF385C;color:#fff;border:none;cursor:pointer;width:100%;padding:12px;border-radius:8px;font-size:16px;font-weight:600;">Save Interests</button>'
        '</div>'
        '</div>'
        '</div>'
    )

    _script = """<script>
var Streamlit={
  setComponentReady:function(){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');},
  setComponentValue:function(v){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setComponentValue',dataType:'json',value:v},'*');},
  setFrameHeight:function(h){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*');}
};
Streamlit.setComponentReady();
(function(){try{var pd=window.parent.document;if(!pd.getElementById('_alp_chrome_css')){var s=pd.createElement('style');s.id='_alp_chrome_css';s.textContent='header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="baseButton-headerNoPadding"],#MainMenu,section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stBottomBlockContainer"]{display:none!important}.main .block-container{padding:0!important;max-width:100%!important}[data-testid="stApp"],.stApp{background:#FFF5F0!important}';pd.head.appendChild(s);}}catch(e){}})();
Streamlit.setFrameHeight(window.parent.innerHeight);

var _nd=document.getElementById('nav-discover');
if(_nd)_nd.closest('a').addEventListener('click',function(e){e.preventDefault();Streamlit.setComponentValue({action:'navigate',page:'browse'});});
var _na=document.getElementById('nav-agent');
if(_na)_na.closest('a').addEventListener('click',function(e){e.preventDefault();Streamlit.setComponentValue({action:'navigate',page:'discover'});});
var _nc=document.getElementById('nav-create');
if(_nc)_nc.closest('a').addEventListener('click',function(e){e.preventDefault();Streamlit.setComponentValue({action:'navigate',page:'discover'});});

function showInterestModal(){document.getElementById('interest-modal').style.display='flex';}
function hideInterestModal(){document.getElementById('interest-modal').style.display='none';}
function saveInterests(){
  var sel=[];
  document.querySelectorAll('.int-cb:checked').forEach(function(cb){sel.push(cb.value);});
  Streamlit.setComponentValue({action:'update_interests',interests:sel});
  hideInterestModal();
}
var _intModal=document.getElementById('interest-modal');
if(_intModal)_intModal.addEventListener('click',function(e){if(e.target===this)hideInterestModal();});
</script>"""

    html = html.replace("</body>", _modal_html + _script + "\n</body>")
    return html


# Generate auth component HTML from design files and declare component
_AUTH_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_component")
os.makedirs(_AUTH_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_AUTH_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write(_build_auth_html())
_auth_component = components.declare_component("auth_gate", path=_AUTH_COMPONENT_DIR)

_ONBOARDING1_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "onboarding1_component")
os.makedirs(_ONBOARDING1_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_ONBOARDING1_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write(_build_onboarding1_html())
_onboarding1_component = components.declare_component("onboarding_step1", path=_ONBOARDING1_COMPONENT_DIR)

_ONBOARDING2_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "onboarding2_component")
os.makedirs(_ONBOARDING2_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_ONBOARDING2_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write(_build_onboarding2_html())
_onboarding2_component = components.declare_component("onboarding_step2", path=_ONBOARDING2_COMPONENT_DIR)

_MAIN_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_component")
os.makedirs(_MAIN_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_MAIN_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write("<!DOCTYPE html><html><body></body></html>")
_main_component = components.declare_component("main_view", path=_MAIN_COMPONENT_DIR)

_CREATE_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "create_component")
os.makedirs(_CREATE_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_CREATE_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write("<!DOCTYPE html><html><body></body></html>")
_create_component = components.declare_component("create_view", path=_CREATE_COMPONENT_DIR)

_PROFILE_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_component")
os.makedirs(_PROFILE_COMPONENT_DIR, exist_ok=True)
with open(os.path.join(_PROFILE_COMPONENT_DIR, "index.html"), "w") as _f:
    _f.write("<!DOCTYPE html><html><body></body></html>")
_profile_component = components.declare_component("profile_view", path=_PROFILE_COMPONENT_DIR)

# Page Config
st.set_page_config(
    page_title="After Work Agent - Discover Activities & Communities",
    page_icon=Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "mascot.jpg")),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide all Streamlit chrome from render 1 onwards (toolbar, header, sidebar, deploy button).
# Injected unconditionally so it applies during auth, onboarding, and main view equally.
st.markdown("""<style>
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="baseButton-headerNoPadding"],
#MainMenu,
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stBottomBlockContainer"] { display: none !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stApp"], .stApp { background: #FFF5F0 !important; }
</style>""", unsafe_allow_html=True)

# Loading splash — always rendered (keeps it in Streamlit's delta tree so it is never
# abruptly removed mid-display on rerender). Visibility toggled by session state.
_splash_vis = not st.session_state.get('_splash_done')
if _splash_vis:
    st.session_state['_splash_done'] = True
_splash_show_css = ('position:fixed;inset:0;background:linear-gradient(160deg,#FFF5F0 0%,#FFF0F5 100%);'
                    'z-index:99999;display:flex;align-items:center;justify-content:center;'
                    'pointer-events:none;animation:_pg_out 0.5s ease 2s forwards')
render_html(f"""
<style>
@keyframes _pg_dot{{0%,80%,100%{{transform:scale(0.6);opacity:0.4}}40%{{transform:scale(1);opacity:1}}}}
@keyframes _pg_in{{from{{opacity:0;transform:scale(0.93)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes _pg_out{{from{{opacity:1}}to{{opacity:0;visibility:hidden}}}}
#_alp_splash{{{_splash_show_css if _splash_vis else 'display:none!important'};}}
#_alp_splash .card{{display:flex;flex-direction:column;align-items:center;gap:20px;
  background:white;border-radius:24px;padding:40px 48px;
  box-shadow:0 8px 40px rgba(255,56,92,0.12),0 2px 12px rgba(0,0,0,0.06);
  animation:_pg_in 0.3s cubic-bezier(0.34,1.56,0.64,1) forwards}}
#_alp_splash .d1{{animation:_pg_dot 1.2s ease-in-out infinite}}
#_alp_splash .d2{{animation:_pg_dot 1.2s ease-in-out 0.2s infinite}}
#_alp_splash .d3{{animation:_pg_dot 1.2s ease-in-out 0.4s infinite}}
</style>
<div id="_alp_splash">
  <div class="card">
    <div style="width:72px;height:72px;border-radius:50%;overflow:hidden;box-shadow:0 4px 16px rgba(255,56,92,0.2)">
      <img src="{_MASCOT_DATA_URI}" style="width:100%;height:100%;object-fit:cover">
    </div>
    <div style="text-align:center">
      <p style="font-family:'Inter',sans-serif;font-size:17px;font-weight:600;color:#222;margin:0 0 4px">ALP</p>
      <p style="font-family:'Inter',sans-serif;font-size:13px;color:#888;margin:0">Finding something great for you...</p>
    </div>
    <div style="display:flex;gap:7px;align-items:center">
      <span class="d1" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>
      <span class="d2" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>
      <span class="d3" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF385C"></span>
    </div>
  </div>
</div>
""")

# Global light-theme styling
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.activity-card {
    background: #FFFFFF;
    border: 1px solid #DDDDDD;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.activity-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
}
.activity-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}
.activity-title {
    font-size: 17px;
    font-weight: 600;
    color: #222222;
}
.custom-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 9999px;
    margin-right: 6px;
    display: inline-block;
    margin-bottom: 4px;
}
.badge-type     { background: #EBF5FF; color: #1D6FA4; border: 1px solid #C5E0F5; }
.badge-location { background: #FFF7E6; color: #B7691B; border: 1px solid #F5DEB3; }
.badge-creator  { background: #EDFAF3; color: #1A7A4A; border: 1px solid #B8EDD3; }
.badge-squad    { background: #F3F0FF; color: #6B35C7; border: 1px solid #D5C8F5; }
.badge-dept     { background: #FFF0F5; color: #B5266B; border: 1px solid #F5C0D8; }
.badge-uncomfort{ background: #FFF5F5; color: #C0392B; border: 1px solid #FFCDD2; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:.8} 50%{opacity:1} }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
</style>
""")


# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "interests_input" not in st.session_state:
    st.session_state.interests_input = ""
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# Session restore is handled browser-side via localStorage in the auth iframe JS.
# The server-side file (_load_session) was removed because it was shared across all users
# on the same server instance, causing user A's session to bleed into user B's tab.

# --- AUTH GATE ---
if "logged_in_user_id" not in st.session_state:
    render_html("""<style>
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
#MainMenu,section[data-testid="stSidebar"],[data-testid="stBottomBlockContainer"]{display:none!important}
.main .block-container{padding:0!important;max-width:100%!important}
</style>""")
    _auth_result = _auth_component(key="auth_gate", default=None)
    if _auth_result and isinstance(_auth_result, dict) and _auth_result.get("token"):
        _uid = int(_auth_result["uid"])
        _tok = str(_auth_result["token"])
        _onboarded = bool(_auth_result.get("onboarded", False))
        st.session_state.session_token = _tok
        st.session_state.logged_in_user_id = _uid
        st.session_state.is_onboarded = _onboarded
        _save_session(_uid, _onboarded, _tok)
        st.rerun()
    st.stop()

# --- ONBOARDING GATE ---
if not st.session_state.get("is_onboarded", True):
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1

    _ob_step = st.session_state.onboarding_step

    if _ob_step == 1:
        render_html("""<style>
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
#MainMenu,section[data-testid="stSidebar"],[data-testid="stBottomBlockContainer"]{display:none!important}
.main .block-container{padding:0!important;max-width:100%!important}
[data-testid="stApp"],.stApp{background:transparent!important;background-color:transparent!important}
</style>""")
        _ob1_result = _onboarding1_component(key="onboarding_step1", default=None)
        if _ob1_result and isinstance(_ob1_result, dict):
            if _ob1_result.get("action") == "back":
                _tok = st.session_state.get("session_token")
                if _tok:
                    api_client.logout(_tok)
                _clear_session()
                for _k in ["logged_in_user_id", "is_onboarded", "session_token", "onboarding_step",
                           "step1_full_name", "step1_horoscope", "step1_business_unit",
                           "step1_department", "step1_org_group", "step1_squad"]:
                    st.session_state.pop(_k, None)
                st.rerun()
            elif _ob1_result.get("action") == "continue":
                _fn = _ob1_result.get("full_name", "").strip()
                if _fn:
                    st.session_state.step1_full_name = _fn
                    st.session_state.step1_horoscope = _ob1_result.get("horoscope", "")
                    st.session_state.step1_business_unit = _ob1_result.get("business_unit", "")
                    st.session_state.step1_department = _ob1_result.get("department", "")
                    st.session_state.step1_org_group = _ob1_result.get("org_group", "")
                    st.session_state.step1_squad = _ob1_result.get("squad", "")
                    st.session_state.onboarding_step = 2
                    st.rerun()
        st.stop()

    render_html("""<style>
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
#MainMenu,section[data-testid="stSidebar"],[data-testid="stBottomBlockContainer"]{display:none!important}
.main .block-container{padding:0!important;max-width:100%!important}
[data-testid="stApp"],.stApp{background:transparent!important;background-color:transparent!important}
</style>""")
    _ob2_result = _onboarding2_component(key="onboarding_step2", default=None)
    if _ob2_result and isinstance(_ob2_result, dict):
        if _ob2_result.get("action") == "back":
            st.session_state.onboarding_step = 1
            st.rerun()
        elif _ob2_result.get("action") == "complete":
            _interests = [i.lower() for i in _ob2_result.get("interests", [])]
            _company = st.session_state.get("step1_business_unit", "Other")
            if _company in ("Select Unit", ""):
                _company = "Other"
            onboarding_data = {
                "full_name": st.session_state.get("step1_full_name", ""),
                "company": _company,
                "org_group": st.session_state.get("step1_org_group", ""),
                "department": st.session_state.get("step1_department", ""),
                "squad": st.session_state.get("step1_squad") or None,
                "interests": _interests,
            }
            if not onboarding_data["full_name"]:
                st.session_state.onboarding_step = 1
                st.rerun()
            else:
                res = api_client.onboard_user(st.session_state.logged_in_user_id, onboarding_data)
                if res:
                    st.session_state.is_onboarded = True
                    _tok = st.session_state.get("session_token")
                    if _tok:
                        _save_session(st.session_state.logged_in_user_id, True, _tok)
                    st.rerun()
    st.stop()

# --- MAIN APP (AUTHENTICATED) ---
current_user = api_client.get_user_profile(st.session_state.logged_in_user_id)
if not current_user:
    st.error("Active profile not found. Please log out and try again.")
    if st.button("🚪 Reset Session"):
        token = st.session_state.get("session_token")
        if token:
            api_client.logout(token)
        _clear_session()
        del st.session_state.logged_in_user_id
        if "is_onboarded" in st.session_state:
            del st.session_state.is_onboarded
        st.session_state.pop("session_token", None)
        st.rerun()
    st.stop()

# ── Main app light theme CSS ──────────────────────────────────────────────────
render_html("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
html, body, .stApp, [data-testid="stApp"] {
    background: #FBFAF9 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
header[data-testid="stHeader"]   { visibility: hidden !important; height: 0 !important; }
#MainMenu                         { display: none !important; }
[data-testid="stToolbar"]         { display: none !important; }
[data-testid="stDecoration"]      { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #DDDDDD !important;
    min-width: 236px !important; max-width: 236px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: #FFFFFF !important;
    padding: 24px 14px 16px 14px !important;
}
.main .block-container {
    max-width: 100% !important;
    padding: 32px 40px 60px 40px !important;
    margin: 0 !important;
}
/* Sidebar nav buttons */
section[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: transparent !important; border: none !important;
    color: #717171 !important; justify-content: flex-start !important;
    text-align: left !important; padding: 12px 16px !important;
    border-radius: 8px !important; font-size: 14px !important;
    font-weight: 600 !important; box-shadow: none !important;
    height: 44px !important; min-height: 44px !important; margin-bottom: 2px !important;
    font-family: 'Inter', sans-serif !important; letter-spacing: 0 !important;
    border-right: 2px solid transparent !important;
    transition: background 0.15s, color 0.15s !important;
}
section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: #F7F5F5 !important; color: #222222 !important;
}
/* Form submit in main */
.main [data-testid="stFormSubmitButton"] > button {
    background: #FF385C !important; color: #FFFFFF !important;
    border: none !important; border-radius: 8px !important;
    height: 52px !important; font-size: 16px !important; font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(255,56,92,0.22) !important;
}
.main [data-testid="stFormSubmitButton"] > button:hover { background: #E00B41 !important; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; }
/* Inputs */
.main .stTextInput > div > div > input,
.main .stNumberInput > div > div > input {
    border: 1px solid #DDDDDD !important; border-radius: 8px !important;
    height: 48px !important; font-size: 14px !important; color: #222222 !important;
    background: #FFFFFF !important;
}
.main .stTextArea > div > div > textarea {
    border: 1px solid #DDDDDD !important; border-radius: 8px !important;
    font-size: 14px !important; color: #222222 !important; background: #FFFFFF !important;
}
.main div[data-baseweb="select"] > div {
    border: 1px solid #DDDDDD !important; border-radius: 8px !important;
    background: #FFFFFF !important; min-height: 48px !important; font-size: 14px !important;
}
.main .stTextInput label p, .main .stSelectbox label p, .main .stTextArea label p,
.main .stNumberInput label p, .main .stDateInput label p, .main .stTimeInput label p {
    font-size: 11px !important; font-weight: 700 !important; color: #5f5e5e !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important;
}
input:focus, textarea:focus {
    outline: none !important;
    box-shadow: none !important;
}
div[data-baseweb="input"] > div,
div[data-baseweb="input"]:focus-within > div {
    outline: none !important;
    box-shadow: none !important;
    background: #FFFFFF !important;
}
div[data-baseweb="select"] > div,
div[data-baseweb="select"]:focus-within > div {
    outline: none !important;
    box-shadow: none !important;
    background: #FFFFFF !important;
}
@keyframes _page_fadein {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.main .block-container {
    animation: _page_fadein 0.25s ease-out;
}
</style>""")

if "page" not in st.session_state:
    st.session_state.page = "discover"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    _cur = st.session_state.get("page", "discover")

    render_html("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:32px;padding-bottom:20px;border-bottom:1px solid #EEEEEE;">
    <div style="width:34px;height:34px;background:linear-gradient(135deg,#FF385C,#c90034);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">🤖</div>
    <span style="font-weight:700;font-size:16px;color:#222222;font-family:'Inter',sans-serif;">AfterWork</span>
</div>""")

    _nav = [
        ("discover", "explore",    "Discover"),
        ("browse",   "__mascot__", "Browse Activities"),
        ("create",   "add_circle", "Create Activity"),
        ("profile",  "person",     "Profile"),
    ]
    for _pk, _ic, _lb in _nav:
        if _ic == "__mascot__":
            _icon_html = f'<img src="{_MASCOT_DATA_URI}" style="width:20px;height:20px;object-fit:cover;border-radius:50%;">' if _MASCOT_DATA_URI else '<span class="material-symbols-outlined" style="font-size:20px">smart_toy</span>'
        else:
            _icon_html = f'<span class="material-symbols-outlined" style="font-size:20px;color:#FF385C;font-variation-settings:\'FILL\' 1;">{_ic}</span>'
        if _cur == _pk:
            render_html(f"""<div style="display:flex;align-items:center;gap:16px;padding:12px 16px;background:#FFF5F7;border-radius:8px;border-right:2px solid #FF385C;margin-bottom:2px;transform:scale(0.98);">
    {_icon_html}
    <span style="font-size:14px;font-weight:700;color:#FF385C;font-family:'Inter',sans-serif;">{_lb}</span>
</div>""")
        else:
            if st.button(_lb, key=f"nav_{_pk}", use_container_width=True):
                st.session_state.page = _pk
                st.rerun()

    render_html('<div style="height:1px;background:#EEEEEE;margin:14px 0;"></div>')

    _notif_key = f"_notifs_{current_user['id']}"
    if _notif_key not in st.session_state:
        st.session_state[_notif_key] = api_client.get_notifications(current_user["id"])
    _notifs = st.session_state[_notif_key]
    _unread = len([n for n in _notifs if not n["read"]])
    with st.expander(f"🔔 Notifications ({_unread})" if _unread else "🔔 Notifications"):
        if not _notifs:
            st.caption("No notifications yet.")
        else:
            for _n in _notifs:
                _ind = "🔵" if not _n["read"] else "⚪"
                try:
                    _ndt = datetime.strptime(_n["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    try:
                        _ndt = datetime.strptime(_n["created_at"], "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        _ndt = datetime.utcnow()
                st.markdown(f"**{_ind}** {_n['message']} *({_ndt.strftime('%b %d, %H:%M')})*")
                if not _n["read"]:
                    if st.button("Mark read", key=f"read_{_n['id']}", use_container_width=True):
                        api_client.mark_notification_read(_n["id"])
                        st.session_state.pop(f"_notifs_{current_user['id']}", None)
                        st.rerun()

    render_html('<div style="height:1px;background:#EEEEEE;margin:10px 0 8px;"></div>')
    render_html(f'<div style="font-size:12px;color:#5f5e5e;padding:2px 16px 8px;font-family:\'Inter\',sans-serif;">{current_user.get("full_name") or current_user["domain"]}</div>')

    with st.expander("⚙️ Settings"):
        st.caption("Dev: wipes all data.")
        if st.button("🗑️ Reset All Data", use_container_width=True):
            _res = api_client.dev_reset()
            if _res.get("success"):
                _clear_session()
                for _k in ["logged_in_user_id", "is_onboarded", "session_token", "chat_history", "conversation_started", "page"]:
                    st.session_state.pop(_k, None)
                st.rerun()
            else:
                st.error(_res.get("message", "Reset failed"))

    if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
        _tok = st.session_state.get("session_token")
        if _tok:
            api_client.logout(_tok)
        _clear_session()
        for _k in ["logged_in_user_id", "is_onboarded", "session_token", "chat_history", "conversation_started", "page"]:
            st.session_state.pop(_k, None)
        st.rerun()

_page = st.session_state.get("page", "discover")

# ── Daily Journal Prompt ─────────────────────────────────────────────────────
if current_user and _page not in ("discover", "browse"):
    _jp_key = f"_jp_{current_user['id']}"
    if _jp_key not in st.session_state:
        st.session_state[_jp_key] = api_client.get_pending_journal_prompt(current_user["id"])
    journal_data = st.session_state[_jp_key]
    if journal_data.get("prompt"):
        target_date_str = journal_data.get("target_date")
        render_html(f"""
<div style="background:#FFF5F7;border:1px solid #FFCDD5;border-radius:12px;padding:16px 20px;margin-bottom:24px;display:flex;align-items:flex-start;gap:14px;">
    <div style="font-size:28px;line-height:1;">📅</div>
    <div>
        <div style="font-size:12px;font-weight:700;color:#FF385C;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">Evening Check-in · {target_date_str}</div>
        <div style="font-size:15px;font-weight:600;color:#222222;font-family:'Inter',sans-serif;">What did you do yesterday evening?</div>
    </div>
</div>""")
        _jopts = journal_data.get("options", [])
        _jcols_count = len(_jopts) + 2
        _jcols = st.columns(_jcols_count)
        _ji = 0
        for _jopt in _jopts:
            _jt = _jopt['title']
            _jshort = _jt[:18] + "…" if len(_jt) > 18 else _jt
            if _jcols[_ji].button(f"✓ {_jshort}", key=f"journal_opt_{_jopt.get('activity_id') or _jopt.get('gym_class_id')}", help=f"Confirm: {_jt}"):
                api_client.resolve_journal_prompt(user_id=current_user["id"], status="resolved_activity",
                    activity_id=_jopt.get("activity_id"), gym_class_id=_jopt.get("gym_class_id"))
                st.session_state.pop(f"_jp_{current_user['id']}", None)
                st.success("Thanks for sharing!")
                st.rerun()
            _ji += 1
        if _jcols[_ji].button("😴 Rested", key="journal_rested"):
            api_client.resolve_journal_prompt(user_id=current_user["id"], status="resolved_no_activity")
            st.session_state.pop(f"_jp_{current_user['id']}", None)
            st.rerun()
        _ji += 1
        if _jcols[_ji].button("Skip", key="journal_skip"):
            api_client.resolve_journal_prompt(user_id=current_user["id"], status="skipped")
            st.session_state.pop(f"_jp_{current_user['id']}", None)
            st.rerun()
        _jother_c1, _jother_c2 = st.columns([3, 1])
        with _jother_c1:
            _jother = st.selectbox("Or something else?", ["football","badminton","running","gym","board games","coffee","ai","zumba","yoga","swimming","other"], key="journal_other_act", label_visibility="collapsed")
        with _jother_c2:
            if st.button("Submit", key="journal_custom_submit", use_container_width=True):
                api_client.resolve_journal_prompt(user_id=current_user["id"], status="resolved_activity", custom_activity=_jother)
                st.session_state.pop(f"_jp_{current_user['id']}", None)
                st.rerun()
        render_html('<div style="height:1px;background:#EEEEEE;margin:16px 0 24px;"></div>')

# ── PAGE: MAIN VIEW (agent chat + discover activities — single component, JS routing) ──
_FULL_PAGE_CSS = """<style>
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
#MainMenu,section[data-testid="stSidebar"],[data-testid="stBottomBlockContainer"]{display:none!important}
.main .block-container{padding:0!important;max-width:100%!important}
[data-testid="stApp"],.stApp{background:transparent!important;background-color:transparent!important}
</style>"""

if _page in ("discover", "browse", "profile") and current_user:
    render_html(_FULL_PAGE_CSS)

    _MAIN_HTML_VER = 22  # bump to force iframe reload after code changes
    if "main_version" not in st.session_state:
        st.session_state.main_version = 0
    if st.session_state.get("_main_html_ver") != _MAIN_HTML_VER:
        st.session_state._main_html_ver = _MAIN_HTML_VER
        st.session_state.main_version = st.session_state.get("main_version", 0) + 1
    if st.session_state.get("_prev_page") not in ("discover", "browse", "profile"):
        st.session_state.main_version += 1
    st.session_state._prev_page = _page

    _fname = (current_user.get("full_name") or current_user["domain"]).split()[-1]
    _uid = current_user["id"]
    _cur_ver = st.session_state.main_version

    # Always render overlay (keeps it in Streamlit's delta tree on every rerender so it is
    # never abruptly removed mid-display). Visibility controlled by _main_overlay_shown.
    _ol_vis = not st.session_state.get("_main_overlay_shown")
    if _ol_vis:
        st.session_state["_main_overlay_shown"] = True
    _ol_show_style = ('position:fixed;inset:0;background:linear-gradient(160deg,#FFF5F0 0%,#FFF0F5 100%);'
                      'z-index:9998;display:flex;align-items:center;justify-content:center;pointer-events:none')
    render_html(f"""
<style>
@keyframes _alp_ol_in{{from{{opacity:0;transform:scale(0.95)}}to{{opacity:1;transform:scale(1)}}}}
</style>
<div id="_alp_main_overlay" style="{_ol_show_style if _ol_vis else 'display:none!important'}">
  <div style="background:white;border-radius:24px;padding:40px 48px;
    box-shadow:0 8px 40px rgba(255,56,92,0.12),0 2px 12px rgba(0,0,0,0.06);
    display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center;
    animation:_alp_ol_in 0.3s cubic-bezier(0.34,1.56,0.64,1) forwards">
    <div style="width:64px;height:64px;border-radius:50%;overflow:hidden;
      box-shadow:0 4px 16px rgba(255,56,92,0.2)">
      <img src="{_MASCOT_DATA_URI}" style="width:100%;height:100%;object-fit:cover">
    </div>
    <div>
      <p style="font-family:'Inter',sans-serif;font-size:17px;font-weight:600;color:#222;margin:0 0 4px">ALP</p>
      <p style="font-family:'Inter',sans-serif;font-size:13px;color:#888;margin:0">Finding something great for you...</p>
    </div>
  </div>
</div>""")

    # Cache API responses by (user_id, main_version) — invalidated whenever main_version bumps
    _recs_ver_key   = f"_rv_{_uid}"
    _browse_ver_key = f"_bv_{_uid}"
    _needs_recs   = st.session_state.get(_recs_ver_key)   != _cur_ver
    _needs_browse = st.session_state.get(_browse_ver_key) != _cur_ver

    if _needs_recs:
        _recs = api_client.get_recommendations(_uid, limit=20)
        st.session_state[f"_rc_{_uid}"] = _recs
        st.session_state[_recs_ver_key] = _cur_ver
    else:
        _recs = st.session_state.get(f"_rc_{_uid}") or []

    if _needs_browse:
        _browse_items = api_client.browse_activities(_uid)
        st.session_state[f"_bc_{_uid}"] = _browse_items
        st.session_state[_browse_ver_key] = _cur_ver
    else:
        _browse_items = st.session_state.get(f"_bc_{_uid}") or []

    _initial_view = 'discover' if _page == 'browse' else ('profile' if _page == 'profile' else 'agent')
    _main_html = _build_main_component_html(_fname, _recs or [], _uid, _initial_view, user=current_user, browse_items=_browse_items or [])
    with open(os.path.join(_MAIN_COMPONENT_DIR, "index.html"), "w") as _mf:
        _mf.write(_main_html)

    _main_result = _main_component(key=f"main_{st.session_state.main_version}", default=None)
    if _main_result and isinstance(_main_result, dict):
        _main_action = _main_result.get("action")
        if _main_action == "join":
            _act_id = _main_result.get("activity_id")
            if _act_id:
                api_client.join_activity(int(_act_id), current_user["id"])
                st.session_state.main_version += 1
                st.rerun()
        elif _main_action == "submit_activity":
            _d = _main_result.get("data", {})
            _date_str = _d.get("date") or date.today().isoformat()
            _ca_res = api_client.create_activity(
                title=_d.get("title", ""),
                description=_d.get("description", ""),
                activity_type=_d.get("activity_type", "other"),
                start_time=f"{_date_str}T{_d.get('start_time','18:00')}:00",
                end_time=f"{_date_str}T{_d.get('end_time','19:00')}:00",
                location=_d.get("location", ""),
                location_type=_d.get("location_type", "off_campus"),
                difficulty=_d.get("difficulty") or None,
                participant_limit=int(_d.get("participant_limit", 10)),
                creator_id=current_user["id"],
                guidelines=_d.get("guidelines", "") or None,
            )
            if _ca_res:
                st.session_state.main_version += 1
                st.rerun()
        elif _main_action == "update_interests":
            _new_ints = _main_result.get("interests", [])
            if api_client.update_user_interests(current_user["id"], _new_ints):
                st.session_state.main_version += 1
                st.rerun()
        elif _main_action == "logout":
            _tok = st.session_state.get("session_token")
            if _tok:
                api_client.logout(_tok)
            for _k in ["logged_in_user_id", "is_onboarded", "session_token", "chat_history", "conversation_started", "page", "_main_overlay_shown"]:
                st.session_state.pop(_k, None)
            st.rerun()

# ── PAGE: CREATE ACTIVITY ─────────────────────────────────────────────────────
elif _page == "create" and current_user:
    render_html(_FULL_PAGE_CSS)
    _fname = (current_user.get("full_name") or current_user["domain"]).split()[-1]
    _create_err = st.session_state.pop("_create_error", "")
    _create_html = _build_create_html(_fname, user_id=current_user["id"], error_msg=_create_err)
    with open(os.path.join(_CREATE_COMPONENT_DIR, "index.html"), "w") as _cf:
        _cf.write(_create_html)
    _create_result = _create_component(key="create_v1", default=None)
    if _create_result and isinstance(_create_result, dict):
        _cr_action = _create_result.get("action")
        if _cr_action == "submit":
            _d = _create_result.get("data", {})
            _date_str = _d.get("date") or date.today().isoformat()
            _start_str = (_d.get("start_time") or "18:00").replace(":", "")[:4]
            _start_str = f"{_start_str[:2]}:{_start_str[2:]}" if len(_start_str) == 4 else _d.get("start_time", "18:00")
            _end_str = (_d.get("end_time") or "19:00").replace(":", "")[:4]
            _end_str = f"{_end_str[:2]}:{_end_str[2:]}" if len(_end_str) == 4 else _d.get("end_time", "19:00")
            _ca_res = api_client.create_activity(
                title=_d.get("title", ""),
                description=_d.get("description", ""),
                activity_type=_d.get("activity_type", "other"),
                start_time=f"{_date_str}T{_d.get('start_time','18:00')}:00",
                end_time=f"{_date_str}T{_d.get('end_time','19:00')}:00",
                location=_d.get("location", ""),
                location_type=_d.get("location_type", "off_campus"),
                difficulty=_d.get("difficulty") or None,
                participant_limit=int(_d.get("participant_limit", 10)),
                creator_id=current_user["id"],
                guidelines=_d.get("guidelines", "") or None,
            )
            if _ca_res:
                st.session_state.page = "discover"
                st.rerun()
            else:
                st.session_state._create_error = "Failed to create activity. Please try again."
                st.rerun()
        elif _cr_action == "navigate":
            _nav_page = _create_result.get("page")
            if _nav_page:
                st.session_state.page = _nav_page
                st.rerun()

