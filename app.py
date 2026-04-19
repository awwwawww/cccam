import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعدادات الصفحة
st.set_page_config(page_title="Ultra Sniper V11", layout="wide")

st.title("🎯 Sniper Elite V11: Automatic Hunter & Checker")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ Control Panel")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("Timeout (sec)", 0.5, 5.0, 2.0)
    max_workers = st.slider("Threads", 50, 300, 150)
    days_to_search = st.number_input("Testious Days", 1, 10, 3)

# دالة الفحص التقني (Handshake)
def verify_server(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        start = time.time()
        
        if sock.connect_ex((host, int(port))) == 0:
            latency = round((time.time() - start) * 1000)
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
    except: pass
    return None

# دالة استخراج السيرفرات المحسنة
def extract_servers(text):
    results = []
    # نمط CCcam
    c_pattern = re.findall(r'(C:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)', text)
    for m in c_pattern: results.append((m[0], m[1], m[2], m[3], m[4], ""))
    # نمط Newcamd
    n_pattern = re.findall(r'(N:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)\s+([0-9a-fA-F ]{20,28})', text)
    for m in n_pattern: results.append(m)
    return list(set(results))

# تنفيذ البحث والفحص التلقائي
if st.button("🚀 Start Auto Hunt & Check", use_container_width=True):
    if not token:
        st.error("Missing GitHub Token")
    else:
        raw_candidates = set()
        today = datetime.now()

        # 1. جلب من Testious
        for i in range(days_to_search):
            d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            try:
                r = requests.get(f"https://testious.com/old-free-cccam-servers/{d}/", timeout=10)
                for s in extract_servers(r.text): raw_candidates.add(s)
            except: pass

        # 2. جلب من Telegram
        channels = ["FreeCCcamServers", "cccam_sharing", "dailycccam2", "CCcamFree4K", "premium_cccam"]
        for ch in channels:
            try:
                r = requests.get(f"https://t.me/s/{ch}", timeout=10)
                for s in extract_servers(r.text): raw_candidates.add(s)
            except: pass

        # 3. جلب من GitHub
        gh_headers = {"Authorization": f"token {token}"}
        yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        queries = [f'"C:" created:>{yesterday}', 'filename:CCcam.cfg']
        for q in queries:
            try:
                api_url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
                res = requests.get(api_url, headers=gh_headers, timeout=15).json()
                for item in res.get('items', [])[:30]:
                    raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    content = requests.get(raw_url, timeout=5).text
                    for s in extract_servers(content): raw_candidates.add(s)
            except: pass

        if raw_candidates:
            st.info(f"Found {len(raw_candidates)} potential servers. Testing...")
            active = []
            progress = st.progress(0)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(verify_server, s): s for s in raw_candidates}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res: active.append(res)
                    progress.progress((i + 1) / len(raw_candidates))
            
            if active:
                st.success(f"✅ {len(active)} Servers Online")
                df = pd.DataFrame(active).sort_values(by="Ping")
                st.dataframe(df[["Type", "Server", "Port", "User", "Ping"]], use_container_width=True)
                
                final_cfg = "\n".join([s['Line'] for s in active])
                st.download_button("📥 Download CCcam.cfg", final_cfg, file_name="CCcam_Live.cfg")
                st.text_area("Live Lines:", value=final_cfg, height=300)
            else:
                st.warning("No active servers found.")
        else:
            st.error("No servers extracted from sources.")

# قسم الفحص اليدوي السريع
st.markdown("---")
st.subheader("🛠️ Manual Input Check")
manual_input = st.text_area("Paste lines here (C: or N:):", height=150)
if st.button("Check Manual Lines"):
    m_candidates = extract_servers(manual_input)
    if m_candidates:
        active_m = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_server, m_candidates))
            active_m = [r for r in results if r is not None]
        
        if active_m:
            st.success(f"Found {len(active_m)} active servers")
            cfg_m = "\n".join([s['Line'] for s in active_m])
            st.download_button("Download Manual .cfg", cfg_m, file_name="Manual_Check.cfg")
            st.text_area("Active Lines:", value=cfg_m, height=150)
        else:
            st.error("All lines are offline.")

st.markdown("---")
st.caption("مطور امين | Support: 01098137253")
