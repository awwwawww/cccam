import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# --- إعدادات الواجهة ---
st.set_page_config(page_title="Ultra Sniper V9 - Mega Hunter", layout="wide")

st.title("🚀 Sniper Elite V9: Mega Hunter Edition")
st.markdown("### تم التوسيع: (تليجرام المكثف + قناص GitHub + Pastebin + محرك فحص الجودة)")

# --- الإعدادات الجانبية ---
with st.sidebar:
    st.header("⚙️ إعدادات مطور أمين")
    token = st.text_input("GitHub Token", type="password", help="ضروري جداً لجلب السيرفرات الطازجة")
    check_timeout = st.slider("سرعة الرد المطلوبة (ثواني)", 0.5, 5.0, 1.5)
    max_workers = st.slider("قوة الفحص (Threads)", 50, 300, 150)
    st.markdown("---")
    st.warning("الفحص الآن يتطلب استجابة حقيقية من السيرفر وليس بورت مفتوح فقط.")

if 'final_servers' not in st.session_state:
    st.session_state.final_servers = []

# --- دالة فحص المصافحة الاحترافية (Handshake) ---
def check_server_quality(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        
        start = time.time()
        # محاولة الاتصال
        if sock.connect_ex((host, int(port))) == 0:
            # قياس البنج
            latency = round((time.time() - start) * 1000)
            
            # فحص بروتوكول CCcam: السيرفر الحقيقي يرسل 16 بايت فوراً
            if prefix.upper() == 'C:':
                greeting = sock.recv(16)
                if len(greeting) < 16:
                    sock.close()
                    return None
            
            sock.close()
            return {
                "Type": prefix.replace(":", ""),
                "Server": host,
                "Port": port,
                "User": user,
                "Pass": pwd,
                "Ping": f"{latency}ms",
                "Line": f"{prefix} {host} {port} {user} {pwd} {deskey}".strip()
            }
    except:
        pass
    return None

# --- محرك القنص الشامل ---
def mega_hunt():
    if not token:
        st.error("❌ بدون GitHub Token لن تجد السيرفرات الجديدة. يرجى إدخاله!")
        return

    raw_candidates = set()
    today_str = datetime.now().strftime('%Y-%m-%d')

    # 1. القنص من تليجرام (أكثر من 15 قناة نشطة جداً)
    st.write("📡 جاري قنص قنوات التليجرام النشطة...")
    tg_channels = [
        "FreeCCcamServers", "cccam_sharing", "dailycccam2", "freecccamnewcamd2023",
        "CCcamFree4K", "iptvcccamfree", "vsh_cccam", "premium_cccam", "cccam_free_server",
        "best_cccam", "cccamsat", "free_cccam_all_world", "cccam_world_free"
    ]
    for channel in tg_channels:
        try:
            r = requests.get(f"https://t.me/s/{channel}", timeout=10)
            # ريجيكس أقوى لاستخراج السيرفرات حتى مع وجود رموز غريبة
            found = re.findall(r'([CN]:)\s*([a-zA-Z0-9\-\.]+)\s+(\d+)\s+([a-zA-Z0-9\-\.\_]+)\s+([a-zA-Z0-9\-\.\_]+)', r.text)
            for f in found: raw_candidates.add((f[0], f[1], f[2], f[3], f[4], ""))
        except: continue

    # 2. القنص من GitHub (البحث عن الملفات المرفوعة "الآن")
    st.write("🐙 جاري فحص GitHub بحثاً عن ملفات .cfg حديثة...")
    gh_headers = {"Authorization": f"token {token}"}
    # البحث عن السطور التي تحتوي على C: وتم تحديثها في آخر 24 ساعة
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    queries = [f'"C:" created:>{yesterday}', f'filename:CCcam.cfg "{today_str}"']
    
    for q in queries:
        try:
            api_url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
            res = requests.get(api_url, headers=gh_headers, timeout=15).json()
            for item in res.get('items', [])[:40]:
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                content = requests.get(raw_url, timeout=5).text
                matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                for m in matches: raw_candidates.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # 3. القنص من Testious (تغطية شاملة لآخر 3 أيام)
    st.write("🌍 جاري فحص Testious الشامل...")
    for i in range(3):
        date_check = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            url = f"https://testious.com/old-free-cccam-servers/{date_check}/"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', r.text)
            for m in matches: raw_candidates.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # --- مرحلة الفلترة والفرز ---
    if raw_candidates:
        st.info(f"⚡ تم تجميع {len(raw_candidates)} سيرفر. جاري تصفية الشغال منها فقط...")
        active_list = []
        progress = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_server_quality, s): s for s in raw_candidates}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                res = future.result()
                if res: active_list.append(res)
                progress.progress((i + 1) / len(raw_candidates))
        
        st.session_state.final_servers = active_list
    else:
        st.error("لم يتم العثور على أي سيرفرات. تأكد من إعدادات البحث!")

# --- واجهة العرض ---
col_start, col_clear = st.columns(2)
with col_start:
    if st.button("🔥 ابدأ الصيد الكبير (Mega Hunt)", use_container_width=True):
        mega_hunt()
with col_clear:
    if st.button("🗑️ مسح النتائج", use_container_width=True):
        st.session_state.final_servers = []
        st.rerun()

if st.session_state.final_servers:
    df = pd.DataFrame(st.session_state.final_servers)
    st.success(f"✅ مبروك! تم العثور على {len(df)} سيرفر شغال ومستجيب.")
    
    # عرض النتائج في جدول مرتب حسب السرعة
    df = df.sort_values(by="Ping")
    st.dataframe(df[["Type", "Server", "Port", "User", "Ping"]], use_container_width=True)
    
    st.markdown("### 📋 الأسطر الجاهزة (انسخها وضعها في ملفك):")
    text_output = "\n".join([s['Line'] for s in st.session_state.final_servers])
    st.text_area("", value=text_output, height=350)
    
    st.download_button("📥 تحميل CCcam.cfg", text_output, file_name=f"Matawar_Amin_{today_str}.txt")
else:
    st.info("اضغط على الزر بالأعلى للبدء.. الصيد قد يستغرق دقيقة لجلب أفضل النتائج.")

st.markdown("---")
st.caption("برمجة وتطوير: مطور أمين | الدعم: vfcash 01098137253")
