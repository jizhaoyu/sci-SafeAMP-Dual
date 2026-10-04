conf_path = "/etc/nginx/conf.d/sub2api.conf"
with open(conf_path, "r", encoding="utf-8") as f:
    text = f.read()

rule = """
    # SafeAMP-Dual 2.0 Web Platform
    location /safeamp/ {
        proxy_pass http://127.0.0.1:8090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

# 在最后一个 location / { 前也插入 (443 ssl 区块)
last_loc = text.rfind("location / {")
if last_loc != -1:
    # 检查前面是否有 safeamp
    pre_chunk = text[max(0, last_loc-200):last_loc]
    if "location /safeamp/" not in pre_chunk:
        text = text[:last_loc] + rule + "\n    " + text[last_loc:]
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(text)
        print("Successfully added /safeamp/ to HTTPS 443 block!")
    else:
        print("HTTPS block already contains /safeamp/!")
