import os, re
directory = 'everycli/data/commands/'
yaml_files = [f for f in os.listdir(directory) if f.endswith(('.yaml', '.yml'))]

pattern = re.compile(r'^(\s*(?:explanation|description|note|warning|tip|example|\-)\s*:?\s+)(?!["\'])(.*ex:\s+`.*)$')

for filename in yaml_files:
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    changed = False
    for line in lines:
        match = pattern.match(line)
        if match:
            prefix = match.group(1)
            val = match.group(2).rstrip().replace('"', '\\"')
            line = f'{prefix}"{val}"\n'
            changed = True
        new_lines.append(line)
        
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            print(f"Fixed {filename}")
