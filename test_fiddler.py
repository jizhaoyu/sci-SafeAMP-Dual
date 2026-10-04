import requests
import json
import time

URL = "http://62.234.141.184/api/ai_optimize"
PROXY = "http://127.0.0.1:8866"
proxies = {
    "http": PROXY,
    "https": PROXY,
}

print(f"🚀 向线上多智能体突变引擎发送高并发请求测试...")
for i in range(3):
    print(f"[{i+1}/3] 发送请求: GIGAVLKVLTTGLPALISWIKRKRQQ (通过 Fiddler {PROXY})")
    try:
        start_time = time.time()
        resp = requests.post(
            URL, 
            json={"sequence": "GIGAVLKVLTTGLPALISWIKRKRQQ"},
            proxies=proxies,
            timeout=30
        )
        end_time = time.time()
        if resp.status_code == 200:
            data = resp.json()
            sol = data.get("solutions", [{}])[0]
            print(f"  ✅ 成功! 耗时: {end_time - start_time:.2f}s | 优化序列: {sol.get('mutated_seq')} | TSI 增益: {sol.get('tsi_gain')}")
        else:
            print(f"  ❌ 失败! HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"  ⚠️ 请求异常: {e}")
    time.sleep(1)

print("✅ 所有测试请求已注入 Fiddler!")
