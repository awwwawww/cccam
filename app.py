import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعدادات الصفحة
st.set_page_config(page_title="Ultra Sniper V15", layout="wide")

st.title("🎯 Sniper Elite V15: Auto-Check Edition")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ Settings")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("Timeout (sec)", 1.0, 5.0, 2.5)
    max_workers = st.slider("Threads", 20, 100, 50)
    days_to_search = st.number_input("Testious Days", 1, 5, 2)

# دالة الفحص الصارم (Handshake)
def verify_server_strict(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        start = time.time()
        
        if sock.connect_ex((host, int(port))) == 0:
            if prefix.upper() == 'C:':
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

# دالة استخراج السيرفرات
def extract_servers(text):
    results = []
    c_pattern = re.findall(r'([CN]:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)', text)
    for m in c_pattern:
        results.append((m[0], m[1], m[2], m[3], m[4], ""))
    return list(set(results))

# تنفيذ البحث والفحص التلقائي
if st.button("🚀 Start Auto Hunt & Verify", use_container_width=True):
    raw_candidates = set()
    today = datetime.now()

    # 1. جلب من Testious
    for i in range(days_to_search):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            r = requests.get(f"https://testious.com/old-free-cccam-servers/{d}/", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            for s in extract_servers(r.text): raw_candidates.add(s)
        except: pass

    # 2. جلب من Telegram
    channels = ["FreeCCcamServers", "cccam_sharing", "dailycccam2", "CCcamFree4K", "vsh_cccam", "premium_cccam"]
    for ch in channels:
        try:
            r = requests.get(f"https://t.me/s/{ch}", timeout=10)
            for s in extract_servers(r.text): raw_candidates.add(s)
        except: pass

    # 3. جلب من GitHub
    if token:
        gh_headers = {"Authorization": f"token {token}"}
        yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        q = f'extension:cfg "C:" created:>{yesterday}'
        try:
            api_url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
            res = requests.get(api_url, headers=gh_headers, timeout=15).json()
            for item in res.get('items', [])[:30]:
                raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                content = requests.get(raw_url, timeout=5).text
                for s in extract_servers(content): raw_candidates.add(s)
        except: pass

    if raw_candidates:
        st.info(f"Found {len(raw_candidates)} potential servers. Verifying...")
        active = []
        progress = st.progress(0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(verify_server_strict, s): s for s in raw_candidates}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                res = future.result()
                if res: active.append(res)
                progress.progress((i + 1) / len(raw_candidates))
        
        if active:
            st.success(f"✅ Found {len(active)} Real Online Servers")
            df = pd.DataFrame(active).sort_values(by="Ping")
            st.dataframe(df[["Type", "Server", "Port", "User", "Ping"]], use_container_width=True)
            
            final_cfg = "\n".join([s['Line'] for s in active])
            st.download_button("📥 Download CCcam.cfg", final_cfg, file_name="Live_Servers.cfg")
            st.text_area("Live Lines:", value=final_cfg, height=300)
        else:
            st.error("No real servers found. All extracted lines are offline.")
    else:
        st.error("Failed to extract servers. Try again later.")

# الفحص اليدوي
st.markdown("---")
st.subheader("🛠️ Manual Input Check")
manual_input = st.text_area("Paste lines here:", height=150)
if st.button("Check Manual Lines"):
    m_candidates = extract_servers(manual_input)
    if m_candidates:
        active_m = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_server_strict, m_candidates))
            active_m = [r for r in results if r is not None]
        
        if active_m:
            st.success(f"Found {len(active_m)} active servers")
            cfg_m = "\n".join([s['Line'] for s in active_m])
            st.download_button("Download .cfg", cfg_m, file_name="Manual_Check.cfg")
            st.text_area("Active Lines:", value=cfg_m, height=150)
        else:
            st.error("All lines failed verification.")

st.markdown("---")
st.caption("مطور امين | 01098137253")
