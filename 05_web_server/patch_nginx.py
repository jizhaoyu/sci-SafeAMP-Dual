conf_path = "/etc/nginx/conf.d/sub2api.conf"
with open(conf_path, "r", encoding="utf-8") as f:
    text = f.read()

rule = """
    # DTI Web Platform
    location /dti/ {
        proxy_pass http://127.0.0.1:8090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

if "/dti/" not in text:
    idx = text.rfind("}")
    if idx != -1:
        new_text = text[:idx] + rule + text[idx:]
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Patched Nginx config for DTI.")
    else:
        print("Could not find closing brace in nginx config.")
else:
    print("DTI location block already present in nginx config.")
