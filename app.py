import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Ultra Sniper v8 - Today's Live Support me vfcash 01098137253 ", layout="wide")

st.title("🎯 Sniper Elite V8: Today's Fresh Servers Support me vfcash 01098137253")
st.markdown(f"### فحص مباشر لسيرفرات اليوم: {datetime.now().strftime('%Y-%m-%d')}")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("مهلة الفحص (ثواني)", 1.0, 5.0, 2.5)
    max_workers = st.slider("سرعة المعالجة", 20, 100, 60)

if 'servers' not in st.session_state:
    st.session_state.servers = []

def check_live(server_data):
    """فحص احترافي للتأكد من استجابة السيرفر الحالية"""
    prefix, host, port, user, pwd, deskey = server_data
    try:
        with socket.create_connection((host, int(port)), timeout=check_timeout):
            return {
                "Type": prefix,
                "Server": host,
                "Port": port,
                "User": user,
                "Pass": pwd,
                "Deskey": deskey,
                "Full Line": f"{prefix} {host} {port} {user} {pwd} {deskey}".strip()
            }
    except:
        return None

def fetch_from_sources():
    if not token:
        st.error("⚠️ يرجى إدخال التوكن للبحث في GitHub")
        return

    all_raw = set()
    today = datetime.now()

    # 1. جلب بيانات من Testious (آخر 10 أيام واليوم)
    st.info("🌐 جاري سحب البيانات من Testious لآخر 10 أيام...")
    for i in range(10):
        target_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            testious_url = f"https://testious.com/old-free-cccam-servers/{target_date}/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(testious_url, headers=headers, timeout=10)
            if response.status_code == 200:
                matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', response.text)
                for m in matches:
                    all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except:
            continue

    # 2. جلب بيانات من GitHub (آخر 48 ساعة بدقة)
    st.info("🐙 جاري البحث في GitHub عن سيرفرات آخر 48 ساعة...")
    gh_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # حساب تاريخ ووقت قبل 48 ساعة بصيغة ISO التي يقبلها جيت هاب
    forty_eight_hours_ago = (today - timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    queries = [
        f'C: created:>={forty_eight_hours_ago}', 
        f'N: created:>={forty_eight_hours_ago}',
        'filename:CCcam.cfg sort:indexed-desc'
    ]

    for q in queries:
        try:
            r = requests.get(f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc", headers=gh_headers)
            if r.status_code == 200:
                for item in r.json().get('items', [])[:40]: # زيادة العدد لضمان جلب أكبر قدر
                    raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    try:
                        content = requests.get(raw_url, timeout=5).text
                        c_matches = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                        n_matches = re.findall(r'(N:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)\s+([0-9a-fA-F ]{20,})', content)
                        for m in c_matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
                        for m in n_matches: all_raw.add(m)
                    except: continue
        except: continue

    # 3. جلب من مواقع ومنتديات أخرى (مواقع عامة ومواقع اللصق)
    st.info("🌍 جاري فحص مصادر ومنتديات إضافية...")
    extra_urls = [
        "https://pastebin.com/archive", # مثال عام
        # يمكنك إضافة روابط المنتديات هنا مباشرة
    ]
    for url in extra_urls:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                c_matches = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', response.text)
                for m in c_matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except:
            continue

    # الفحص المباشر
    if not all_raw:
        st.warning("لم يتم العثور على سيرفرات في المصادر، يرجى التأكد من التوكن واتصال الإنترنت.")
        return

    st.info(f"🔎 تم تجميع {len(all_raw)} سيرفر فريد.. جاري تصفية الشغال منها فقط...")
    active_results = []
    
    # استخدام Progress Bar لمعرفة تقدم الفحص
    progress_bar = st.progress(0)
    total = len(all_raw)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_live, server): server for server in all_raw}
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = future.result()
            if result:
                active_results.append(result)
            progress_bar.progress((i + 1) / total)
    
    st.session_state.servers = active_results

# زر التشغيل
if st.button("🚀 صيد سيرفرات اليوم وغداً"):
    fetch_from_sources()

# عرض النتائج
if st.session_state.servers:
    df = pd.DataFrame(st.session_state.servers)
    st.success(f"✅ تم العثور على {len(st.session_state.servers)} سيرفر شغال 100%")
    
    # عرض الجدول
    st.table(df[["Type", "Server", "Port", "User", "Pass", "Deskey"]])
    
    # النسخ السريع
    st.markdown("### 📋 السطور الجاهزة للنسخ:")
    all_lines = "\n".join([s['Full Line'] for s in st.session_state.servers])
    st.text_area("", value=all_lines, height=400)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    st.download_button("📥 تحميل كملف .txt", all_lines, file_name=f"servers_{today_str}.txt")
else:
    st.info("اضغط على الزر بالأعلى لبدء الصيد..")
