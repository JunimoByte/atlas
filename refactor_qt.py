import os
import re

src_dir = r'c:\Users\Michael\Documents\GitHub\atlas\src'

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'PyQt6' not in content and 'PyQt5' not in content and 'PyQt ' not in content and 'pyqtSignal' not in content:
        return
        
    print(f'Processing {filepath}')
    
    # We will do some manual string replacements for the comments
    content = content.replace('separation from PyQt signals', 'separation from Qt signals')
    content = content.replace('PyQt-agnostic', 'Qt-agnostic')
    content = content.replace('dependency on PyQt', 'dependency on Qt')
    content = content.replace('PyQt signals', 'Qt signals')
    content = content.replace('PyQt', 'Qt') # Catch all other comments, but might affect imports? Let's be careful.
    
    # Reload original content to avoid messing up imports before regex matching
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace('separation from PyQt signals', 'separation from Qt signals')
    content = content.replace('PyQt-agnostic', 'Qt-agnostic')
    content = content.replace('dependency on PyQt', 'dependency on Qt')
    content = content.replace('PyQt signals', 'Qt signals')
    
    # Matches `from PyQt6.QtCore import A, B`
    # Also handles multiline with parenthesis: `from PyQt6.QtWidgets import (\n A,\n B\n)`
    import_pattern = re.compile(r'from\s+PyQt[56]\.(\w+)\s+import\s+(?:\((.*?)\)|(.*?))(?=\n\S|\Z)', re.MULTILINE | re.DOTALL)
    
    imports_to_add = set()
    replacements = {}
    
    def replacer(match):
        module = match.group(1) # e.g. QtCore
        imports_to_add.add(module)
        
        # Get the imported names
        names_str = match.group(2) if match.group(2) else match.group(3)
        names = [n.strip() for n in names_str.replace('\n', '').split(',') if n.strip()]
        
        for name in names:
            replacements[name] = f'{module}.{name}'
            
        return f'from atlas.compatibility.qt import {module}'
    
    new_content = import_pattern.sub(replacer, content)
    
    # Sort keys by length descending to prevent partial matches issue (e.g. QAbstractButton vs QAbstractButtonBox)
    for name in sorted(replacements.keys(), key=len, reverse=True):
        module = replacements[name].split('.')[0]
        # Regex to replace whole word `name` not preceded by a dot or a quote
        # Need to handle strings? Usually no PyQt classes are exactly string names we want to keep, but let's just do word boundaries.
        new_content = re.sub(rf'(?<!\.)\b{name}\b', replacements[name], new_content)

    # Some manual fixes for comments or docstrings that might have been messed up?
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
