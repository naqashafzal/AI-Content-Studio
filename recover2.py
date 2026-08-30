import json
import re
import os

log_path = r"C:\Users\naqas\.gemini\antigravity-ide\brain\8137f358-1449-4095-9d58-3cb1fedcaf7c\.system_generated\logs\transcript.jsonl"
file_contents = {}
latest_write = {}

def apply_replacements(content, chunks):
    for chunk in chunks:
        target = chunk.get('TargetContent', '')
        replacement = chunk.get('ReplacementContent', '')
        if target and target in content:
            content = content.replace(target, replacement)
    return content

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except:
                continue
                
            if 'tool_calls' in entry:
                for tc in entry['tool_calls']:
                    name = tc.get('name', '')
                    args_raw = tc.get('args') or tc.get('arguments')
                    if not isinstance(args_raw, dict):
                        continue
                        
                    args = {}
                    for k, v in args_raw.items():
                        if isinstance(v, str):
                            try:
                                args[k] = json.loads(v)
                            except:
                                args[k] = v
                        else:
                            args[k] = v
                            
                    target_file = args.get('TargetFile', '').lower()
                    if not target_file.endswith('.tsx') or 'web\\src' not in target_file:
                        target_file = target_file.replace('/', '\\')
                        if not target_file.endswith('.tsx') or 'web\\src' not in target_file:
                            continue

                    if 'write_to_file' in name:
                        file_contents[target_file] = args.get('CodeContent', '')
                        latest_write[target_file] = 'write'
                    elif 'multi_replace_file_content' in name:
                        if target_file in file_contents:
                            file_contents[target_file] = apply_replacements(file_contents[target_file], args.get('ReplacementChunks', []))
                            latest_write[target_file] = 'multi_replace'
                    elif 'replace_file_content' in name:
                        if target_file in file_contents:
                            target_content = args.get('TargetContent', '')
                            rep_content = args.get('ReplacementContent', '')
                            if target_content in file_contents[target_file]:
                                file_contents[target_file] = file_contents[target_file].replace(target_content, rep_content)
                                latest_write[target_file] = 'replace'
                                
            # Check for view_file response
            if entry.get('type') == 'TOOL_RESPONSE' and 'view_file' in entry.get('content', ''):
                content = entry.get('content', '')
                match = re.search(r'File Path: `file:///(.*?)`', content)
                if match:
                    path_str = match.group(1).replace('/', '\\').lower()
                    if '.tsx' in path_str and 'web\\src' in path_str:
                        lines_part = content.split('The following code has been modified')
                        if len(lines_part) > 1:
                            lines_raw = lines_part[1].split('The above content')[0]
                            lines = []
                            for l in lines_raw.split('\n'):
                                m = re.match(r'^\d+: (.*)', l)
                                if m:
                                    lines.append(m.group(1))
                            
                            if len(lines) > 0:
                                new_content = "\n".join(lines)
                                if len(new_content) > len(file_contents.get(path_str, "")):
                                    file_contents[path_str] = new_content
                                    latest_write[path_str] = 'view_file'

except Exception as e:
    print("Error:", e)

for path, content in file_contents.items():
    if content.strip():
        idx = path.find('web\\src')
        if idx != -1:
            clean_path = os.path.join(r"C:\Users\naqas\OneDrive\Desktop\Prog\AI-Content-Studio", path[idx:])
            print(f"Recovered {clean_path} ({len(content)} bytes) from {latest_write.get(path)}")
            try:
                os.makedirs(os.path.dirname(clean_path), exist_ok=True)
                with open(clean_path, 'w', encoding='utf-8') as out:
                    out.write(content)
            except Exception as e:
                print("Write error", e)
