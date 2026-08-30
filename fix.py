import glob
import json
import ast

for filepath in glob.glob('web/src/**/*.tsx', recursive=True):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if content.startswith('"'):
            # It's a JSON string. Parse it twice to unescape it properly.
            try:
                parsed = json.loads(content)
            except Exception as e:
                print("json loads failed for", filepath, e)
                try:
                    parsed = ast.literal_eval(content)
                except:
                    continue
                    
            if isinstance(parsed, str) and parsed.startswith('"'):
                try:
                    parsed = json.loads(parsed)
                except:
                    try:
                        parsed = ast.literal_eval(parsed)
                    except:
                        pass
                        
            if isinstance(parsed, str):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(parsed)
                print("Fixed", filepath)
    except Exception as e:
        print("Error on", filepath, e)
