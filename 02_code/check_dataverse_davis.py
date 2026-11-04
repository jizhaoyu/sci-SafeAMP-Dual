import json

with open(r'C:\Users\888\.gemini\antigravity\brain\31e23736-661c-450a-87fc-1798ec3a4b9f\.system_generated\steps\191\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

json_start = text.find('{')
data = json.loads(text[json_start:])
files = data['data']['latestVersion']['files']
print(f"Total files in Dataverse: {len(files)}")
for f in files:
    fn = f.get('dataFile', {}).get('filename', '')
    if 'davis' in fn.lower():
        df = f['dataFile']
        print(f"File ID: {df['id']}, Name: {fn}, Size: {df['filesize']}, MD5: {df.get('md5')}")
