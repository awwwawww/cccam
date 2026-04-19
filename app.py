import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعداد الصفحة
st.set_page_config(page_title="Ultra Sniper v8 - Extreme Edition", layout="wide")

st.title("🎯 Sniper Elite V8: Extreme Edition")
st.markdown("### نظام صيد السيرفرات الطازجة وفلترة السيرفرات الميتة")
st.info("تم تحديث الفحص ليتناسب مع سرعة الاستجابة الحقيقية للسيرفر")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ إعدادات المطور امين")
    token = st.text_input("GitHub Token", type="password")
    max_ping = st.slider("أقصى وقت استجابة (ثانية)", 0.5, 3.0, 1.2)
    max_workers = st.slider("سرعة المعالجة (توازي)", 20, 100, 70)

if 'servers' not in st.session_state:
    st.session_state.servers = []

def check_server_quality(server_data):
    """فحص الجودة: يتأكد من أن السيرفر ليس فقط متصل، بل سريع الاستجابة"""
    prefix, host, port, user, pwd, deskey = server_data
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(max_ping)
        
        # محاولة الاتصال
        result = sock.connect_ex((host, int(port)))
        
        if result == 0:
            # قياس وقت الاستجابة (Ping)
            latency = round((time.time() - start_time) * 1000, 2)
            
            # فحص بروتوكولي أعمق
            if prefix.upper() == 'C:':
                data = sock.recv(16)
                if not data: 
                    sock.close()
                    return None
            
            sock.close()
            return {
                "Type": prefix.replace(":", ""),
                "Server": host,
                "Port": port,
                "User": user,
                "Pass": pwd,
                "Latency": f"{latency} ms",
                "Full Line": f"{prefix} {host} {port} {user} {pwd} {deskey}".strip()
            }
    except:
        pass
    return None

def fetch_fresh_data():
    if not token:
        st.error("⚠️ يرجى وضع GitHub Token")
        return

    all_raw = set()
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 1. جلب من مصادر متجددة (GitHub البحث المتقدم)
    st.info("🚀 جاري صيد السيرفرات الطازجة من GitHub...")
    gh_headers = {"Authorization": f"token {token}"}
    
    # البحث عن الملفات التي تم تحديثها اليوم فقط
    queries = [
        f'path:CCcam.cfg "{today_str}"',
        f'"C:" extension:cfg created:>{yesterday_str}',
        'filename:CCcam.cfg'
    ]

    for q in queries:
        try:
            api_url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
            r = requests.get(api_url, headers=gh_headers, timeout=10)
            if r.status_code == 200:
                items = r.json().get('items', [])
                for item in items[:25]:
                    raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    content = requests.get(raw_url, timeout=5).text
                    # استخراج السطور
                    c_matches = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                    n_matches = re.findall(r'(N:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)\s+([0-9a-fA-F ]{20,})', content)
                    for m in c_matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
                    for m in n_matches: all_raw.add(m)
        except: continue

    # 2. جلب من Testious (اليوم والأمس فقط لضمان الحداثة)
    for d in [today_str, yesterday_str]:
        try:
            url = f"https://testious.com/old-free-cccam-servers/{d}/"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if res.status_code == 200:
                matches = re.findall(r'([CN]:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', res.text)
                for m in matches: all_raw.add((m[0], m[1], m[2], m[3], m[4], ""))
        except: continue

    # تصفية وفحص
    if all_raw:
        st.info(f"🔎 تم تجميع {len(all_raw)} سيرفر مرشح.. جاري الفحص عن طريق 'مطور امين'...")
        results = []
        progress = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(check_server_quality, s): s for s in all_raw}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                res = future.result()
                if res:
                    results.append(res)
                progress.progress((i + 1) / len(all_raw))
        
        st.session_state.servers = results
    else:
        st.error("لم يتم العثور على أي سيرفرات جديدة حالياً.")

# التحكم
if st.button("🔥 ابدأ الصيد الاحترافي"):
    fetch_fresh_data()

# عرض النتائج
if st.session_state.servers:
    df = pd.DataFrame(st.session_state.servers)
    # ترتيب حسب السرعة (الأسرع أولاً)
    df['sort_val'] = df['Latency'].str.replace(' ms', '').astype(float)
    df = df.sort_values('sort_val').drop(columns=['sort_val'])
    
    st.success(f"✅ تم العثور على {len(df)} سيرفر شغال بجودة عالية")
    st.dataframe(df[["Type", "Server", "Port", "User", "Pass", "Latency"]], use_container_width=True)
    
    st.markdown("### 📋 السطور الجاهزة (الأسرع في الأعلى):")
    lines = "\n".join([s['Full Line'] for s in df.to_dict('records')])
    st.text_area("", value=lines, height=300)
    
    st.download_button("📥 تحميل ملف CCcam.cfg", lines, file_name=f"Sniper_V8_{today_str}.txt")
else:
    st.info("بانتظار بدء الصيد...")

st.markdown("---")
st.caption("مطور امين | Support vfcash: 01098137253")
