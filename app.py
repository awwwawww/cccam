import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Ultra Sniper V10 - Pro Edition", layout="wide")

st.title("🎯 Sniper Elite V10: Pro Checker & Hunter")
st.markdown("### الأداة المتكاملة: صيد السيرفرات + صندوق فحص يدوي + استخراج ملف CFG")

# --- الإعدادات الجانبية ---
with st.sidebar:
    st.header("⚙️ إعدادات مطور أمين")
    token = st.text_input("GitHub Token", type="password")
    check_timeout = st.slider("مهلة الفحص (ثواني)", 0.5, 4.0, 1.5)
    max_workers = st.slider("قوة المعالجة (Threads)", 50, 300, 150)
    st.markdown("---")
    st.info("الصندوق اليدوي يسمح لك بفحص سيرفراتك الخاصة وتصدير الشغال منها فقط.")

# --- الدوال الأساسية ---

def verify_server(data):
    """فحص المصافحة (Handshake) لضمان أن السيرفر حقيقي"""
    prefix, host, port, user, pwd, deskey = data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(check_timeout)
        start = time.time()
        
        if sock.connect_ex((host, int(port))) == 0:
            latency = round((time.time() - start) * 1000)
            # فحص بروتوكول CCcam
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

def extract_servers(text):
    """استخراج السيرفرات من أي نص خام"""
    # البحث عن نمط C: و N:
    c_matches = re.findall(r'(C:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)', text)
    n_matches = re.findall(r'(N:)\s*([^\s#<]+)\s+(\d+)\s+([^\s#<]+)\s+([^\s#<]+)\s+([0-9a-fA-F ]{20,28})', text)
    
    results = []
    for m in c_matches: results.append((m[0], m[1], m[2], m[3], m[4], ""))
    for m in n_matches: results.append(m)
    return list(set(results))

# --- تقسيم الواجهة إلى تبويبين (Tabs) ---
tab1, tab2 = st.tabs(["🔎 صيد السيرفرات تلقائياً", "🛠️ صندوق الفحص اليدوي (Testious Mode)"])

# --- التبويب الأول: الصيد التلقائي ---
with tab1:
    if st.button("🔥 ابدأ الصيد الكبير (تليجرام + جيت هاب + ويب)"):
        if not token:
            st.error("يرجى إدخال التوكن في القائمة الجانبية")
        else:
            candidates = set()
            # جلب من تليجرام
            st.write("📡 قنص التليجرام...")
            tg_channels = ["FreeCCcamServers", "cccam_sharing", "dailycccam2", "CCcamFree4K"]
            for ch in tg_channels:
                try:
                    r = requests.get(f"https://t.me/s/{ch}", timeout=10)
                    for s in extract_servers(r.text): candidates.add(s)
                except: pass
            
            # جلب من Testious اليوم
            st.write("🌍 فحص Testious اليوم...")
            today_str = datetime.now().strftime('%Y-%m-%d')
            try:
                r = requests.get(f"https://testious.com/old-free-cccam-servers/{today_str}/", timeout=10)
                for s in extract_servers(r.text): candidates.add(s)
            except: pass

            if candidates:
                st.info(f"تم جمع {len(candidates)} سيرفر. جاري الفحص...")
                active = []
                progress = st.progress(0)
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(verify_server, s): s for s in candidates}
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        res = future.result()
                        if res: active.append(res)
                        progress.progress((i + 1) / len(candidates))
                
                if active:
                    st.success(f"✅ تم إيجاد {len(active)} سيرفر متصل.")
                    df = pd.DataFrame(active)
                    st.dataframe(df[["Type", "Server", "Port", "User", "Ping"]], use_container_width=True)
                    cfg_content = "\n".join([s['Line'] for s in active])
                    st.download_button("📥 تحميل ملف CCcam.cfg للشغال فقط", cfg_content, file_name="Cccam_Hunted.cfg")
                else:
                    st.warning("لا يوجد سيرفرات متصلة حالياً.")

# --- التبويب الثاني: صندوق الفحص اليدوي ---
with tab2:
    st.subheader("📋 الصندوق الاحترافي لفحص السطور")
    st.info("ضع السطور الخاصة بك هنا (C: أو N:) وسيقوم المطور أمين بفحصها واستخراج الشغال منها فقط.")
    
    input_text = st.text_area("ألصق السيرفرات هنا:", height=250, placeholder="C: server.com 12000 user pass")
    
    if st.button("✅ ابدأ فحص الصندوق اليدوي"):
        manual_candidates = extract_servers(input_text)
        if not manual_candidates:
            st.error("لم يتم العثور على صيغ سيرفرات صحيحة في النص!")
        else:
            st.info(f"جاري فحص {len(manual_candidates)} سيرفر مضاف...")
            active_manual = []
            progress_m = st.progress(0)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(verify_server, s): s for s in manual_candidates}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res: active_manual.append(res)
                    progress_m.progress((i + 1) / len(manual_candidates))
            
            if active_manual:
                st.success(f"🎉 تم تصفية {len(active_manual)} سيرفر شغال من أصل {len(manual_candidates)}")
                df_m = pd.DataFrame(active_manual)
                st.table(df_m[["Type", "Server", "Port", "User", "Ping"]])
                
                final_cfg = "\n".join([s['Line'] for s in active_manual])
                st.download_button("📥 تحميل ملف CCcam.cfg للريسيفر", final_cfg, file_name="CCcam_Manual_Checked.cfg")
                st.text_area("السطور الشغالة للنسخ السريع:", value=final_cfg, height=150)
            else:
                st.error("للأسف، جميع السيرفرات المضافة غير متصلة (Offline).")

st.markdown("---")
st.caption("برمجة وتطوير: مطور أمين | الدعم الفني: vfcash 01098137253")
