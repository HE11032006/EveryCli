import os
import re

directory = 'everycli/data/commands/'
yaml_files = [f for f in os.listdir(directory) if f.endswith(('.yaml', '.yml'))]

# Regex to find lines like:
#   key: value with : inside
#   - value with : inside
# that are NOT quoted

pattern_key = re.compile(r'^(\s*(?:description|explanation|example|note|warning|tip|command|yaml):\s+)(?!["\'>|])(.*:\s.*)$')
pattern_list = re.compile(r'^(\s*-\s+)(?!["\'>|])(.*:\s.*)$')

for filename in yaml_files:
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    changed = False
    for line in lines:
        original = line
        # Check key: value
        match = pattern_key.match(line)
        if match:
            # quote the value, escaping any existing double quotes
            val = match.group(2).replace('"', '\\"')
            line = f'{match.group(1)}"{val}"\n'
            changed = True
        else:
            # Check list item
            match2 = pattern_list.match(line)
            if match2:
                # Make sure it's not a mapping like - "key": "value"
                val = match2.group(2)
                if not val.strip().startswith('{') and not val.strip().startswith('['):
                    val_escaped = val.replace('"', '\\"')
                    line = f'{match2.group(1)}"{val_escaped}"\n'
                    changed = True
        
        new_lines.append(line)
        
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Fixed {filename}")

print("Done.")
