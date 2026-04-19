import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# إعدادات الصفحة
st.set_page_config(page_title="Ultra Sniper V12", layout="wide")

st.title("🎯 Sniper Elite V12: Real Handshake Checker")

# الإعدادات الجانبية
with st.sidebar:
    st.header("⚙️ Control Panel")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("Timeout (sec)", 1.0, 5.0, 3.0) # زيادة المهلة لضمان استلام البيانات
    max_workers = st.slider("Threads", 20, 100, 50) # تقليل الخيوط يزيد الدقة
    days_to_search = st.number_input("Testious Days", 1, 10, 2)

# دالة الفحص الصارم (Strict Handshake)
def verify_server_strict(data):
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        
        start = time.time()
        # محاولة الاتصال
        if sock.connect_ex((host, int(port))) == 0:
            if prefix.upper() == 'C:':
                # بروتوكول CCcam يرسل 16 بايت (NodeID + Random)
                # السيرفرات الوهمية قد تفتح البورت ولا ترسل شيئاً
                data_received = sock.recv(16)
                
                # إذا استلمنا أقل من 16 بايت أو كانت البيانات "أصفار" فقط، فالسيرفر وهمي
                if len(data_received) == 16 and data_received != b'\x00'*16:
                    latency = round((time.time() - start) * 1000)
                    sock.close()
                    return {
                        "Type": "CCcam", "Server": host, "Port": port,
                        "User": user, "Pass": pwd, "Ping": f"{latency}ms",
                        "Line": f"C: {host} {port} {user} {pwd}"
                    }
            
            elif prefix.upper() == 'N:':
                # نيوكامد يحتاج إرسال بيانات لبدء المصافحة
                sock.send(b'\x00\x00')
                if sock.recv(10):
                    latency = round((time.time() - start) * 1000)
                    sock.close()
                    return {
                        "Type": "Newcamd", "Server": host, "Port": port,
                        "User": user, "Pass": pwd, "Ping": f"{latency}ms",
                        "Line": f"N: {host} {port} {user} {pwd} {deskey}"
                    }
        sock.close()
    except: pass
    return None

def extract_servers(text):
    results = []
    c_pattern = re.findall(r'(C:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)', text)
    for m in c_pattern: results.append((m[0], m[1], m[2], m[3], m[4], ""))
    n_pattern = re.findall(r'(N:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)\s+([0-9a-fA-F ]{20,28})', text)
    for m in n_pattern: results.append(m)
    return list(set(results))

# زر الصيد والفحص التلقائي
if st.button("🚀 Start Auto Hunt & Strict Check", use_container_width=True):
    if not token:
        st.error("Missing GitHub Token")
    else:
        raw_candidates = set()
        # جلب من Testious و Telegram و GitHub
        try:
            # Testious
            for i in range(days_to_search):
                d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                r = requests.get(f"https://testious.com/old-free-cccam-servers/{d}/", timeout=10)
                for s in extract_servers(r.text): raw_candidates.add(s)
            
            # Telegram (المصادر الأكثر ثقة)
            for ch in ["FreeCCcamServers", "cccam_sharing", "dailycccam2"]:
                r = requests.get(f"https://t.me/s/{ch}", timeout=10)
                for s in extract_servers(r.text): raw_candidates.add(s)
        except: pass

        if raw_candidates:
            st.info(f"Checking {len(raw_candidates)} servers with Strict Mode...")
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
                st.download_button("📥 Download CCcam.cfg", final_cfg, file_name="Verified_Live.cfg")
                st.text_area("Live Lines:", value=final_cfg, height=300)
            else:
                st.warning("No real servers responded. Try increasing Timeout.")

st.markdown("---")
st.subheader("🛠️ Manual Input Check (Strict Mode)")
manual_input = st.text_area("Paste lines to verify:", height=150)
if st.button("Verify Manual Lines"):
    m_candidates = extract_servers(manual_input)
    if m_candidates:
        active_m = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_server_strict, m_candidates))
            active_m = [r for r in results if r is not None]
        
        if active_m:
            st.success(f"Verified {len(active_m)} active servers")
            cfg_m = "\n".join([s['Line'] for s in active_m])
            st.download_button("Download .cfg", cfg_m, file_name="Manual_Verified.cfg")
            st.text_area("Active Lines:", value=cfg_m, height=150)
        else:
            st.error("All lines failed strict verification.")

st.markdown("---")
st.caption("مطور امين | 01098137253")
