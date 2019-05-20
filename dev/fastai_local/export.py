
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev/00_export.ipynb

import json,fire,re,os,shutil,glob
from pathlib import Path

def is_root(path): return (Path(path)/'.root').exists()

def export_dest(fname):
    "Returns the destination for an export coming from `fname`"
    fn = Path(fname)
    while not is_root(fn): fn = fn.parent
    return fn/'fastai'/Path(fname).relative_to(fn)

def check_re_pattern(cell, pat):
    "Check if `cell` contains given `pat`."
    if cell['cell_type'] != 'code': return False
    src = cell['source']
    if len(src) == 0: return False
    return re.match(pat, src[0], re.IGNORECASE)

def is_export(cell, default):
    "Check if `cell` is to be exported and returns the name of the module."
    if check_re_pattern(cell, r'^\s*#\s*exports?\s*$'): return default
    tst = check_re_pattern(cell, r'^\s*#\s*exports?\s*(\S+)\s*$')
    return os.path.sep.join(tst.groups()[0].split('.')) if tst else None

def find_default_export(cells):
    for cell in cells:
        tst = check_re_pattern(cell, r'^\s*#\s*default_exp\s*(\S*)\s*$')
        if tst is not None: return tst.groups()[0]

def notebook2scriptSingle(fname):
    "Finds cells starting with `#export` and puts them into a new module"
    fname = Path(fname)
    nb = json.load(open(fname,'r'))
    default = find_default_export(nb['cells'])
    default = os.path.sep.join(default.split('.'))
    fname_out = Path.cwd()/'fastai_local'/f'{default}.py'
    code_cells = [c for c in nb['cells'] if is_export(c, default) is not None]
    module = f'''
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev/{fname.name}

'''
    for cell in code_cells: module += ''.join(cell['source'][1:]) + '\n\n'
    # remove trailing spaces
    module = re.sub(r' +$', '', module, flags=re.MULTILINE)
    output_path = fname.parent/'exp'/fname_out
    open(output_path,'w').write(module[:-2])
    print(f"Converted {fname} to {output_path}")