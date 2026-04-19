import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعداد الصفحة بنمط احترافي
st.set_page_config(page_title="Sniper Elite V8 - Mega Search", layout="wide")

st.title("🎯 Sniper Elite V8: Mega Search Edition")
st.markdown("### المحرك الشامل لجلب سيرفرات (تليجرام + جيت هاب + تيستيوس + ويب)")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ إعدادات مطور أمين")
    token = st.text_input("GitHub Token", type="password", help="ضروري للبحث المتقدم في جيت هاب")
    timeout = st.slider("مهلة الفحص (ثواني)", 1.0, 5.0, 2.0)
    threads = st.slider("عدد الخيوط (السرعة)", 50, 200, 100)
    
    st.markdown("---")
    st.info("هذا الإصدار يبحث في قنوات التليجرام العامة وصفحات الويب المفتوحة.")

if 'found_servers' not in st.session_state:
    st.session_state.found_servers = []

# --- دالة الفحص الاحترافي ---
def verify_server(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # محاولة الاتصال بالبورت
        if sock.connect_ex((host, int(port))) == 0:
            # قياس زمن الاستجابة
            latency = round((time.time() - start_time) * 1000)
            
            # فحص المصافحة لبروتوكول CCcam
            if prefix.upper() == 'C:':
                # السيرفر الشغال يرسل 16 بايت فور الاتصال
                greeting = sock.recv(16)
                if len(greeting) < 16:
                    sock.close()
                    return None
            
            sock.close()
            return {
                "نوع": "CCcam" if prefix.upper() == 'C:' else "Newcamd",
                "السيرفر": host,
                "البورت": port,
                "المستخدم": user,
                "كلمة السر": pwd,
                "الاستجابة": f"{latency}ms",
                "السطر": f"{prefix} {host} {port} {user} {pwd} {deskey}".strip()
            }
    except:
        pass
    return None

# --- دالة جلب البيانات من المصادر المتعددة ---
def start_mega_hunt():
    if not token:
        st.error("⚠️ يرجى إدخال GitHub Token للوصول لمحركات البحث")
        return

    all_raw = set()
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 1. جلب من Testious (اليوم وآخر 48 ساعة)
    st.write("🌐 جاري فحص Testious...")
    for d in [today_str, yesterday_str]:
        try:
            url = f"https://testious.com/old-free-cccam-servers/{d}/"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', r.text)
            for m in matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # 2. جلب من Telegram (عن طريق Web Preview للقنوات المشهورة)
    st.write("📱 جاري فحص قنوات Telegram العامة...")
    telegram_channels = [
        "https://t.me/s/FreeCCcamServers",
        "https://t.me/s/cccam_sharing",
        "https://t.me/s/dailycccam2",
        "https://t.me/s/freecccamnewcamd2023"
    ]
    for channel in telegram_channels:
        try:
            r = requests.get(channel, timeout=10)
            matches = re.findall(r'([CN]:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)', r.text)
            for m in matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # 3. جلب من GitHub (البحث العميق عن ملفات التكوين المحدثة)
    st.write("🐙 جاري البحث المتقدم في GitHub...")
    gh_headers = {"Authorization": f"token {token}"}
    dorks = [
        f'"{today_str}" "C:" filename:CCcam.cfg',
        f'extension:cfg "C:" created:>{yesterday_str}',
        f'"{today_str}" "N:" extension:txt'
    ]
    for q in dorks:
        try:
            api_url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
            res = requests.get(api_url, headers=gh_headers, timeout=10).json()
            for item in res.get('items', [])[:20]:
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                content = requests.get(raw_url, timeout=5).text
                c_m = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                n_m = re.findall(r'(N:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)\s+([0-9a-fA-F ]{20,})', content)
                for m in c_m: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
                for m in n_m: all_raw.add(m)
        except: continue

    # --- مرحلة التنظيف والفحص ---
    if all_raw:
        st.info(f"✅ تم جمع {len(all_raw)} سيرفر مرشح. جاري فحص الجودة الآن...")
        active = []
        progress = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(verify_server, s): s for s in all_raw}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                if result:
                    active.append(result)
                progress.progress((i + 1) / len(all_raw))
        
        st.session_state.found_servers = active
    else:
        st.error("لم يتم العثور على بيانات جديدة. تأكد من اتصالك أو جرب لاحقاً.")

# واجهة المستخدم
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🚀 ابدأ البحث الشامل (تليجرام + ويب + جيت)", use_container_width=True):
        start_mega_hunt()
with col2:
    if st.button("🗑️ مسح القائمة", use_container_width=True):
        st.session_state.found_servers = []
        st.rerun()

# عرض النتائج
if st.session_state.found_servers:
    df = pd.DataFrame(st.session_state.found_servers)
    st.success(f"✅ تم العثور على {len(df)} سيرفر متصل وشغال 100%")
    
    # عرض جدول تفاعلي
    st.dataframe(df[["نوع", "السيرفر", "البورت", "المستخدم", "الاستجابة"]], use_container_width=True)
    
    # السطور الجاهزة
    st.markdown("### 📋 السطور الجاهزة للنسخ:")
    all_lines = "\n".join([s['السطر'] for s in st.session_state.found_servers])
    st.text_area("", value=all_lines, height=300)
    
    st.download_button("📥 تحميل ملف CCcam.cfg", all_lines, file_name=f"Mega_Sniper_{today_str}.txt")
else:
    st.info("بانتظار بدء عملية البحث...")

st.markdown("---")
st.caption("برمجة: مطور أمين | Support vfcash: 01098137253")
