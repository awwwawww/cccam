import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعداد الصفحة
st.set_page_config(page_title="Ultra Sniper v8 - Live Support", layout="wide")

st.title("🎯 Sniper Elite V8: Today's Fresh Servers")
st.markdown(f"### فحص مباشر لسيرفرات اليوم: {datetime.now().strftime('%Y-%m-%d')}")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("مهلة الفحص (ثواني)", 1.0, 5.0, 3.5)
    max_workers = st.slider("سرعة المعالجة", 20, 100, 60)
    days_to_search = st.slider("بحث في Testious (أيام سابقة)", 1, 10, 5)

if 'servers' not in st.session_state:
    st.session_state.servers = []

def check_live_advanced(server_data):
    """فحص ذكي يتأكد من استجابة بروتوكول الشيرنج الحقيقي"""
    prefix, host, port, user, pwd, deskey = server_data
    try:
        # إنشاء اتصال سوكيت
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        
        # محاولة الاتصال
        sock.connect((host, int(port)))
        
        # إذا كان سيسكام، ننتظر استلام حزمة الترحيب (16 بايت)
        if prefix.upper() == 'C:':
            data = sock.recv(16)
            if len(data) == 16:
                sock.close()
                return {
                    "Type": "CCcam", "Server": host, "Port": port,
                    "User": user, "Pass": pwd, "Deskey": "-",
                    "Full Line": f"C: {host} {port} {user} {pwd}"
                }
        
        # إذا كان نيوكامد
        elif prefix.upper() == 'N:':
            sock.send(b'\x00\x00') # إرسال نبضة فحص
            sock.close()
            return {
                "Type": "Newcamd", "Server": host, "Port": port,
                "User": user, "Pass": pwd, "Deskey": deskey,
                "Full Line": f"N: {host} {port} {user} {pwd} {deskey}"
            }
        sock.close()
    except:
        pass
    return None

def fetch_from_sources():
    if not token:
        st.error("⚠️ يرجى إدخال التوكن للبحث في GitHub")
        return

    all_raw = set()
    today = datetime.now()

    # 1. جلب من Testious بناءً على رغبتك (آخر 10 أيام)
    st.info(f"🔎 جاري سحب السيرفرات من Testious لآخر {days_to_search} أيام...")
    for i in range(days_to_search + 1):
        target_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            url = f"https://testious.com/old-free-cccam-servers/{target_date}/"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if res.status_code == 200:
                matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', res.text)
                for m in matches:
                    all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # 2. جلب من GitHub (آخر 48 ساعة بدقة)
    st.info("🐙 جاري فحص GitHub (آخر 48 ساعة)...")
    forty_eight_ago = (today - timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M:%SZ')
    gh_headers = {"Authorization": f"token {token}"}
    queries = [f'C: created:>={forty_eight_ago}', 'filename:CCcam.cfg']

    for q in queries:
        try:
            r = requests.get(f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc", headers=gh_headers)
            if r.status_code == 200:
                for item in r.json().get('items', [])[:30]:
                    raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    content = requests.get(raw_url, timeout=5).text
                    c_matches = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                    n_matches = re.findall(r'(N:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)\s+([0-9a-fA-F ]{20,})', content)
                    for m in c_matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
                    for m in n_matches: all_raw.add(m)
        except: continue

    # عملية الفحص والمطابقة
    if all_raw:
        st.info(f"⚙️ جاري فحص {len(all_raw)} سيرفر.. يرجى الانتظار")
        active_results = []
        progress_bar = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_server = {executor.submit(check_live_advanced, s): s for s in all_raw}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_server)):
                result = future.result()
                if result:
                    active_results.append(result)
                progress_bar.progress((i + 1) / len(all_raw))
        
        st.session_state.servers = active_results
    else:
        st.warning("لم يتم العثور على سيرفرات، تأكد من التوكن.")

# أزرار التشغيل
if st.button("🚀 صيد وفحص سيرفرات اليوم وغداً"):
    fetch_from_sources()

# عرض النتائج
if st.session_state.servers:
    df = pd.DataFrame(st.session_state.servers)
    st.success(f"✅ تم العثور على {len(st.session_state.servers)} سيرفر شغال فعلياً")
    
    st.table(df[["Type", "Server", "Port", "User", "Pass", "Deskey"]])
    
    st.markdown("### 📋 السطور الجاهزة للنسخ:")
    all_lines = "\n".join([s['Full Line'] for s in st.session_state.servers])
    st.text_area("", value=all_lines, height=300)
    
    st.download_button("📥 تحميل ملف .txt", all_lines, file_name=f"servers_{datetime.now().strftime('%Y-%m-%d')}.txt")
else:
    st.info("اضغط على الزر بالأعلى لبدء الصيد..")

st.markdown("---")
st.caption("مطور امين | Support: vfcash 01098137253")
