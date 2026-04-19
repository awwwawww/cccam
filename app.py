import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="Ultra Sniper V14 - Pro Hunter", layout="wide")
st.title("🚀 Sniper Elite V14: Real-Time Server Hunter")

with st.sidebar:
    st.header("⚙️ Control Panel")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("Timeout", 1.0, 5.0, 2.5)
    max_workers = st.slider("Threads", 20, 100, 40)

def verify_server_strict(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        start = time.time()
        
        if sock.connect_ex((host, int(port))) == 0:
            if prefix.upper() == 'C:':
                # الفحص الحقيقي: انتظار استلام أول 16 بايت من بروتوكول CCcam
                # السيرفرات المحظورة أو الوهمية ستغلق الاتصال هنا
                greeting = sock.recv(16)
                if len(greeting) >= 16:
                    latency = round((time.time() - start) * 1000)
                    sock.close()
                    return {
                        "Type": "CCcam", "Server": host, "Port": port,
                        "User": user, "Pass": pwd, "Ping": f"{latency}ms",
                        "Line": f"C: {host} {port} {user} {pwd}"
                    }
        sock.close()
    except: pass
    return None

def extract_all_possible_servers(text):
    found = []
    # نمط استخراج دقيق للسيرفرات
    pattern = re.findall(r'([CN]:)\s*([a-zA-Z0-9\-\.]+)\s+(\d+)\s+([a-zA-Z0-9\.\_\@]+)\s+([a-zA-Z0-9\.\_\@]+)', text)
    for m in pattern:
        found.append((m[0], m[1], m[2], m[3], m[4], ""))
    return list(set(found))

# عملية الصيد والفحص المدمجة
if st.button("🔥 Hunt & Auto-Check Now", use_container_width=True):
    raw_list = set()
    
    # 1. جلب من مصادر تليجرام المباشرة (Live Feed)
    tg_channels = [
        "https://t.me/s/FreeCCcamServers", "https://t.me/s/cccam_sharing", 
        "https://t.me/s/dailycccam2", "https://t.me/s/CCcamFree4K",
        "https://t.me/s/vsh_cccam", "https://t.me/s/premium_cccam"
    ]
    for url in tg_urls:
        try:
            r = requests.get(url, timeout=10)
            for s in extract_all_possible_servers(r.text): raw_list.add(s)
        except: pass

    # 2. جلب من GitHub بأحدث الملفات المرفوعة (Real-time Uploads)
    if token:
        gh_headers = {"Authorization": f"token {token}"}
        # البحث عن ملفات التكوين التي تم تحديثها اليوم
        q = f'extension:cfg "C:"'
        try:
            res = requests.get(f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc", headers=gh_headers, timeout=15).json()
            for item in res.get('items', [])[:20]:
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                content = requests.get(raw_url, timeout=5).text
                for s in extract_all_possible_servers(content): raw_list.add(s)
        except: pass

    if raw_list:
        st.info(f"Found {len(raw_list)} servers. Verifying connection...")
        active = []
        progress = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(verify_server_strict, s): s for s in raw_list}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                res = future.result()
                if res: active.append(res)
                progress.progress((i + 1) / len(raw_list))
        
        if active:
            st.success(f"✅ Found {len(active)} ACTIVE servers!")
            df = pd.DataFrame(active).sort_values(by="Ping")
            st.dataframe(df[["Type", "Server", "Port", "User", "Ping"]], use_container_width=True)
            
            final_cfg = "\n".join([s['Line'] for s in active])
            st.download_button("📥 Download CCcam.cfg", final_cfg, file_name="Cccam_Sniper_V14.cfg")
            st.text_area("Live Lines:", value=final_cfg, height=300)
        else:
            st.error("No active servers found. Most free lines are currently blocked.")
    else:
        st.error("Failed to extract servers. Try again in a few minutes.")

st.markdown("---")
st.subheader("🛠️ Quick Checker (Manual)")
manual_box = st.text_area("Paste lines to test:")
if st.button("Check Manual"):
    m_list = extract_all_possible_servers(manual_box)
    if m_list:
        with st.spinner("Testing..."):
            active_m = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(verify_server_strict, m_list))
                active_m = [r for r in results if r is not None]
            if active_m:
                st.success(f"Found {len(active_m)} working lines")
                st.text_area("Live Only:", value="\n".join([s['Line'] for s in active_m]), height=150)
            else: st.error("All lines are offline or blocked.")

st.caption("مطور امين | 01098137253")
