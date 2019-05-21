#AUTOGENERATED! DO NOT EDIT! File to edit: dev/99_export.ipynb (unless otherwise specified).

__all__ = ['read_nb', 'check_re', 'is_export', 'find_default_export', 'func_class_names', 'notebook2script']

from ..core import *

from ..test import *

from ..imports import *

import nbformat

def read_nb(fname):
    "Read the notebook in `fname`."
    with open(Path(fname),'r') as f: return nbformat.reads(f.read(), as_version=4)

def check_re(cell, pat):
    if cell['cell_type'] != 'code': return False
    return re.match(pat, cell['source'], re.IGNORECASE | re.MULTILINE)

def is_export(cell, default):
    "Check if `cell` is to be exported and returns the name of the module."
    if check_re(cell, r'^\s*#\s*exports?\s*$'):
        if default is None: print(f"This cell doesn't have an export destination and was ignored:\n{cell['source'][1]}")
        return default
    tst = check_re(cell, r'^\s*#\s*exports?\s*(\S+)\s*$')
    return os.path.sep.join(tst.groups()[0].split('.')) if tst else None

def find_default_export(cells):
    "Find in `cells` the default export module."
    for cell in cells:
        tst = check_re(cell, r'^\s*#\s*default_exp\s*(\S*)\s*$')
        if tst: return tst.groups()[0]

def _create_mod_file(fname, nb_path):
    "Create a module file for `fname`."
    fname.parent.mkdir(parents=True, exist_ok=True)
    with open(fname, 'w') as f:
        f.write(f"#AUTOGENERATED! DO NOT EDIT! File to edit: dev/{nb_path.name} (unless otherwise specified).")
        f.write('\n\n__all__ = []')

def func_class_names(code):
    "Find the names of the function or class in "
    names = re.findall(r'^(?:def|class)\s+([^\(\s]*)\s*\(', code, re.MULTILINE)
    return [n for n in names if not n.startswith('_')]

def _add2add(fname, names, line_width=120):
    if len(names) == 0: return
    with open(fname, 'r') as f: text = f.read()
    tw = TextWrapper(width=120, initial_indent='', subsequent_indent=' '*11, break_long_words=False)
    re_all = re.search(r'__all__\s*=\s*\[([^\]]*)\]', text)
    start,end = re_all.start(),re_all.end()
    text_all = tw.wrap(f"{text[start:end-1]}{'' if text[end-2]=='[' else ', '}{', '.join(names)}]")
    with open(fname, 'w') as f: f.write(text[:start] + '\n'.join(text_all) + text[end:])

def _relative_import(name, fname):
    mods = name.split('.')
    splits = str(fname).split(os.path.sep)
    if mods[0] not in splits: return name
    splits = splits[splits.index(mods[0]):]
    while splits[0] == mods[0]: splits,mods = splits[1:],mods[1:]
    return '.' * (len(splits)-len(mods)+1) + '.'.join(mods)

def _deal_import(code_lines, fname):
    pat = re.compile(r'from (fastai_local.\S*) import (\S*)$')
    lines = []
    for line in code_lines:
        match = re.match(pat, line)
        if match: lines.append(f"from {_relative_import(match.groups()[0], fname)} import {match.groups()[1]}\n")
        else: lines.append(line)
    return lines

def _notebook2script(fname):
    "Finds cells starting with `#export` and puts them into a new module"
    fname = Path(fname)
    nb = read_nb(fname)
    default = find_default_export(nb['cells'])
    if default is not None:
        default = os.path.sep.join(default.split('.'))
        _create_mod_file(Path.cwd()/'fastai_local'/f'{default}.py', fname)
    exports = [is_export(c, default) for c in nb['cells']]
    cells = [(c,e) for (c,e) in zip(nb['cells'],exports) if e is not None]
    for (c,e) in cells:
        fname_out = Path.cwd()/'fastai_local'/f'{e}.py'
        orig = '' if e==default else f'#Comes from {fname.name}.\n'
        code = '\n\n' + orig + '\n'.join(_deal_import(c['source'].split('\n')[1:], fname_out))
        # remove trailing spaces
        _add2add(fname_out, [f"'{f}'" for f in _func_class_names(code)])
        code = re.sub(r' +$', '', code, flags=re.MULTILINE)
        with open(fname_out, 'a') as f: f.write(code)
    print(f"Converted {fname}.")

def _get_sorted_files(all_fs: Union[bool,str], up_to=None):
    "Return the list of files corresponding to `g` in the current dir."
    if (all_fs==True): ret = glob.glob('*.ipynb') # Checks both that is bool type and that is True
    else: ret = glob.glob(all_fs) if isinstance(g,str) else []
    if len(ret)==0: print('WARNING: No files found')
    if up_to is not None: ret = [f for f in ret if str(f)<=str(up_to)]
    return sorted(ret)

def notebook2script(fname=None, all_fs=None, up_to=None):
    # initial checks
    assert fname or all_fs
    if (all_fs is None) and (up_to is not None): all_fs=True # Enable allFiles if upTo is present
    fnames = _get_sorted_files(all_fs, up_to=up_to) if all_fs else [fname]
    [_notebook2script(f) for f in fnames]