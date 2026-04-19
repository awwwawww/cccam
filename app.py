import streamlit as st
import requests
import re
import socket
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="Ultra Sniper Server 2026", layout="wide")

st.title("🚀 Monster Hunter: CCcam & Newcamd Web Sniper")
st.markdown("### البحث عن أحدث السيرفرات المنشورة (آخر 48 ساعة)")

# المدخلات في الشريط الجانبي
with st.sidebar:
    st.header("⚙️ الإعدادات")
    github_token = st.text_input("GitHub Token", type="password", help="أدخل التوكن الخاص بك بصلاحية repo")
    search_limit = st.slider("عدد الروابط للفحص", 10, 200, 50)
    threads = st.slider("سرعة الفحص (Threads)", 20, 100, 50)
    
    if st.button("🧹 تنظيف النتائج"):
        st.session_state.results = []

# تهيئة مخزن النتائج
if 'results' not in st.session_state:
    st.session_state.results = []

def check_server(server_data):
    prefix, host, port, user, password, deskey = server_data
    try:
        # فحص الاتصال (Testious Logic)
        with socket.create_connection((host, int(port)), timeout=2.0):
            return {
                "Type": prefix,
                "Server": host,
                "Port": port,
                "User": user,
                "Pass": password,
                "Deskey": deskey if deskey else "",
                "Full Line": f"{prefix} {host} {port} {user} {password} {deskey if deskey else ''}".strip()
            }
    except:
        return None

def fetch_servers():
    if not github_token:
        st.error("❌ يرجى إدخال GitHub Token أولاً!")
        return

    headers = {"Authorization": f"token {github_token}"}
    # البحث عن آخر 48 ساعة
    date_limit = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    queries = [
        f'C: extension:cfg created:>{date_limit}',
        f'N: extension:txt created:>{date_limit}',
        'filename:CCcam.cfg sort:indexed-desc',
        'filename:newcamd.list sort:indexed-desc'
    ]

    all_raw_servers = set()
    progress_bar = st.progress(0)
    st.info("📡 جاري تمشيط GitHub عن أحدث الملفات...")

    for idx, q in enumerate(queries):
        try:
            url = f"https://api.github.com/search/code?q={q}&sort=indexed&order=desc"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                items = r.json().get('items', [])[:search_limit]
                for item in items:
                    raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    content = requests.get(raw_url, timeout=5).text
                    
                    # Regex للسيسكام والنيوكامد (يشمل Deskey للنيوكامد)
                    # CCcam: C: host port user pass
                    cccam_matches = re.findall(r'(C:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)', content)
                    for m in cccam_matches:
                        all_raw_servers.add((m[0], m[1], m[2], m[3], m[4], ""))
                    
                    # Newcamd: N: host port user pass deskey
                    newcamd_matches = re.findall(r'(N:)\s*([^\s#]+)\s+(\d+)\s+([^\s#]+)\s+([^\s#]+)\s+([0-9a-fA-F ]{20,})', content)
                    for m in newcamd_matches:
                        all_raw_servers.add(m)
            progress_bar.progress((idx + 1) / len(queries))
        except:
            continue

    st.success(f"🔎 تم العثور على {len(all_raw_servers)} سيرفر محتمل. جاري الفحص الآن...")
    
    # الفحص المتوازي
    active_servers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(check_server, all_raw_servers))
        active_servers = [r for r in results if r is not None]
    
    st.session_state.results = active_servers

# زر التشغيل الرئيسي
if st.button("🔥 إطلاق الصيد الضخم"):
    fetch_servers()

# عرض النتائج
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    st.markdown("### ✅ السيرفرات الشغالة حالياً")
    
    # عرض الجدول
    st.dataframe(df[["Type", "Server", "Port", "User", "Pass", "Deskey"]], use_container_width=True)
    
    # منطقة النسخ
    st.markdown("### 📋 انسخ السطور من هنا:")
    text_to_copy = "\n".join([item['Full Line'] for item in st.session_state.results])
    st.text_area("السطور الجاهزة:", value=text_to_copy, height=300)
    
    # زر تحميل ملف
    st.download_button(
        label="📥 تحميل النتائج كملف text",
        data=text_to_copy,
        file_name=f"servers_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )
else:
    st.warning("لا توجد نتائج حالياً. اضغط على الزر بالأعلى للبدء.")