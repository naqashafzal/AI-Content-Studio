import json
import re

log_path = r"C:\Users\naqas\.gemini\antigravity-ide\brain\8137f358-1449-4095-9d58-3cb1fedcaf7c\.system_generated\logs\transcript.jsonl"

file_contents = {}

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        # We can extract the file contents from write_to_file calls
        # and also from view_file tool responses.
        try:
            entry = json.loads(line)
            # Check for tool calls
            if 'tool_calls' in entry:
                for tc in entry['tool_calls']:
                    if tc.get('name') == 'default_api:write_to_file':
                        args = tc.get('arguments', {})
                        if isinstance(args, str):
                            import ast
                            try:
                                args = ast.literal_eval(args)
                            except:
                                try:
                                    args = json.loads(args)
                                except:
                                    continue
                        
                        target_file = args.get('TargetFile', '').lower()
                        if '.tsx' in target_file:
                            file_contents[target_file] = args.get('CodeContent', '')
                            
            # Check for view_file response
            if entry.get('type') == 'TOOL_RESPONSE' and 'view_file' in entry.get('content', ''):
                content = entry.get('content', '')
                match = re.search(r'File Path: `file:///(.*?)`', content)
                if match:
                    path_str = match.group(1).replace('/', '\\').lower()
                    if '.tsx' in path_str:
                        lines_part = content.split('The following code has been modified')
                        if len(lines_part) > 1:
                            lines_raw = lines_part[1].split('The above content')[0]
                            lines = []
                            for l in lines_raw.split('\n'):
                                m = re.match(r'^\d+: (.*)', l)
                                if m:
                                    lines.append(m.group(1))
                                elif l.strip() == "":
                                    lines.append("")
                            if len(lines) > 0:
                                current_len = len(file_contents.get(path_str, ""))
                                new_len = len("\n".join(lines))
                                if new_len > current_len:
                                    file_contents[path_str] = "\n".join(lines)
                                    
        except Exception as e:
            continue

for path, content in file_contents.items():
    if content.strip():
        # Clean path to match workspace
        clean_path = path.replace('c:\\users\\naqas\\onedrive\\desktop\\prog\\ai-content-studio\\', '')
        print(f"Recovered {clean_path} ({len(content)} bytes)")
        try:
            import os
            os.makedirs(os.path.dirname(clean_path), exist_ok=True)
            with open(clean_path, 'w', encoding='utf-8') as out:
                out.write(content)
        except Exception as e:
            print("Write error", e)

