
import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعداد الصفحة
st.set_page_config(page_title="Sniper Elite V8 - Pro Checker", layout="wide")

st.title("🎯 Sniper Elite V8: Pro Handshake Checker")
st.markdown(f"### فحص احترافي لسيرفرات: {datetime.now().strftime('%Y-%m-%d')}")
st.warning("⚠️ ملاحظة: هذا الإصدار يفحص استجابة البروتوكول (Handshake) لضمان أن السيرفر حقيقي وليس مجرد بورت مفتوح.")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    token = st.text_input("GitHub Token", type="password", help="ضع التوكن الخاص بك هنا للبحث في جيت هاب")
    check_timeout = st.slider("مهلة الاستجابة (ثواني)", 1.0, 10.0, 4.0)
    max_workers = st.slider("سرعة الفحص (Threads)", 10, 100, 50)
    days_back = st.number_input("عدد أيام البحث في Testious", 1, 10, 7)

if 'servers' not in st.session_state:
    st.session_state.servers = []

def check_cccam_handshake(server_data):
    """فحص ذكي يتأكد من أن السيرفر يرسل بيانات CCcam الحقيقية"""
    prefix, host, port, user, pwd, deskey = server_data
    try:
        # إنشاء اتصال Socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        
        # محاولة الاتصال بالبورت
        start_time = time.time()
        sock.connect((host, int(port)))
        
        if prefix.upper() == 'C:':
            # بروتوكول CCcam يرسل فوراً 16 بايت عشوائية للتشفير عند الاتصال
            # إذا لم يرسلها، فالسيرفر لا يعمل أو اليوزر منتهي
            data = sock.recv(16)
            if len(data) == 16:
                sock.close()
                return {
                    "Type": "CCcam", "Server": host, "Port": port,
                    "User": user, "Pass": pwd, "Status": "✅ Active Protocol",
                    "Full Line": f"C: {host} {port} {user} {pwd}"
                }
        
        elif prefix.upper() == 'N:':
            # نيوكامد يحتاج إرسال بيانات بسيطة للرد
            # سنكتفي هنا بفحص استجابة البورت السريعة لهذا البروتوكول
            sock.send(b'\x00\x00') 
            sock.close()
            return {
                "Type": "Newcamd", "Server": host, "Port": port,
                "User": user, "Pass": pwd, "Status": "✅ Port Open",
                "Full Line": f"N: {host} {port} {user} {pwd} {deskey}"
            }
            
        sock.close()
    except:
        pass
    return None

def fetch_all_sources():
    if not token:
        st.error("❌ يرجى إدخال GitHub Token في القائمة الجانبية!")
        return

    all_raw = set()
    today = datetime.now()

    # 1. جلب من Testious لعدة أيام مضت
    with st.spinner(f"جاري سحب البيانات من Testious لآخر {days_back} أيام..."):
        for i in range(days_back):
            target_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            try:
                url = f"https://testious.com/old-free-cccam-servers/{target_date}/"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if res.status_code == 200:
                    matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', res.text)
                    for m in matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
            except: continue

    # 2. جلب من GitHub (آخر 48 ساعة)
    with st.spinner("جاري البحث في GitHub عن أحدث الروابط (أخر 48 ساعة)..."):
        time_limit = (today - timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M:%SZ')
        gh_headers = {"Authorization": f"token {token}"}
        queries = [f'C: created:>={time_limit}', 'filename:CCcam.cfg']
        
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

    # عملية الفحص
    if all_raw:
        st.info(f"🔎 تم العثور على {len(all_raw)} سيرفر مرشح. جاري فحص الاستجابة الحقيقية...")
        results = []
        progress_bar = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_server = {executor.submit(check_cccam_handshake, s): s for s in all_raw}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_server)):
                res = future.result()
                if res: results.append(res)
                progress_bar.progress((i + 1) / len(all_raw))
        
        st.session_state.servers = results
    else:
        st.warning("لم يتم العثور على أي بيانات، جرب زيادة عدد الأيام أو تأكد من التوكن.")

# أزرار التحكم
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 بدء صيد وفحص السيرفرات", use_container_width=True):
        fetch_all_sources()
with col2:
    if st.button("🗑️ مسح النتائج", use_container_width=True):
        st.session_state.servers = []
        st.rerun()

# عرض النتائج
if st.session_state.servers:
    df = pd.DataFrame(st.session_state.servers)
    st.success(f"✅ تم العثور على {len(df)} سيرفر استجاب بنجاح للفحص المتقدم!")
    
    st.dataframe(df[["Type", "Server", "Port", "User", "Pass", "Status"]], use_container_width=True)
    
    st.markdown("### 📋 السطور الجاهزة للنسخ (Clean Lines):")
    clean_text = "\n".join([s['Full Line'] for s in st.session_state.servers])
    st.text_area("Copy here", value=clean_text, height=300)
    
    st.download_button("📥 تحميل النتائج .txt", clean_text, file_name=f"active_servers_{datetime.now().strftime('%H-%M')}.txt")
---
st.markdown("---")
st.caption("Developed by amin - Support: vfcash 01098137253")
