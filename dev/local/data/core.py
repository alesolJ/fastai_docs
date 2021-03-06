#AUTOGENERATED! DO NOT EDIT! File to edit: dev/04_data_core.ipynb (unless otherwise specified).

__all__ = ['get_files', 'FileGetter', 'image_extensions', 'get_image_files', 'ImageGetter', 'RandomSplitter',
           'GrandparentSplitter', 'parent_label', 'RegexLabeller', 'show_image', 'show_title', 'show_titled_image',
           'show_image_batch', 'Categorize', 'TfmDataLoader', 'Cuda', 'MaskedTransform', 'ByteToFloatTensor',
           'Normalize', 'DataBunch']

from ..imports import *
from ..test import *
from ..core import *
from .pipeline import *
from .external import *
from ..notebook.showdoc import show_doc

def _get_files(p, fs, extensions=None):
    p = Path(p)
    res = [p/f for f in fs if not f.startswith('.')
           and ((not extensions) or f'.{f.split(".")[-1].lower()}' in extensions)]
    return res

def get_files(path, extensions=None, recurse=True, include=None):
    "Get all the files in `path` with optional `extensions`, optionally with `recurse`."
    path = Path(path)
    extensions = setify(extensions)
    extensions = {e.lower() for e in extensions}
    if recurse:
        res = []
        for i,(p,d,f) in enumerate(os.walk(path)): # returns (dirpath, dirnames, filenames)
            if include is not None and i==0: d[:] = [o for o in d if o in include]
            else:                            d[:] = [o for o in d if not o.startswith('.')]
            res += _get_files(p, f, extensions)
    else:
        f = [o.name for o in os.scandir(path) if o.is_file()]
        res = _get_files(path, f, extensions)
    return L(res)

def FileGetter(suf='', extensions=None, recurse=True, include=None):
    "Create `get_files` partial function that searches path suffix `suf` and passes along args"
    def _inner(o, extensions=extensions, recurse=recurse, include=include): return get_files(o/suf, extensions, recurse, include)
    return _inner

image_extensions = set(k for k,v in mimetypes.types_map.items() if v.startswith('image/'))

def get_image_files(path, recurse=True, include=None):
    "Get image files in `path` recursively."
    return get_files(path, extensions=image_extensions, recurse=recurse, include=include)

def ImageGetter(suf='', recurse=True, include=None):
    "Create `get_image_files` partial function that searches path suffix `suf` and passes along `kwargs`"
    def _inner(o, recurse=recurse, include=include): return get_image_files(o/suf, recurse, include)
    return _inner

def RandomSplitter(valid_pct=0.2, seed=None, **kwargs):
    "Create function that splits `items` between train/val with `valid_pct` randomly."
    def _inner(o, **kwargs):
        if seed is not None: torch.manual_seed(seed)
        rand_idx = L(int(i) for i in torch.randperm(len(o)))
        cut = int(valid_pct * len(o))
        return rand_idx[cut:],rand_idx[:cut]
    return _inner

def _grandparent_idxs(items, name): return mask2idxs(Path(o).parent.parent.name == name for o in items)

def GrandparentSplitter(train_name='train', valid_name='valid'):
    "Split `items` from the grand parent folder names (`train_name` and `valid_name`)."
    def _inner(o, **kwargs):
        return _grandparent_idxs(o, train_name),_grandparent_idxs(o, valid_name)
    return _inner

def parent_label(o, **kwargs):
    "Label `item` with the parent folder name."
    return o.parent.name if isinstance(o, Path) else o.split(os.path.sep)[-1]

def RegexLabeller(pat):
    "Label `item` with regex `pat`."
    pat = re.compile(pat)
    def _inner(o, **kwargs):
        res = pat.search(str(o))
        assert res,f'Failed to find "{pat}" in "{o}"'
        return res.group(1)
    return _inner

def show_image(im, ax=None, figsize=None, title=None, ctx=None, **kwargs):
    "Show a PIL image on `ax`."
    ax = ifnone(ax,ctx)
    if ax is None: _,ax = plt.subplots(figsize=figsize)
    # Handle pytorch axis order
    if isinstance(im,Tensor) and im.shape[0]<5: im=im.permute(1,2,0)
    # Handle 1-channel images
    if im.shape[-1]==1: im=im[...,0]
    ax.imshow(im, **kwargs)
    if title is not None: ax.set_title(title)
    ax.axis('off')
    return ax

def show_title(o, ax=None, ctx=None):
    "Set title of `ax` to `o`, or print `o` if `ax` is `None`"
    ax = ifnone(ax,ctx)
    if ax is None: print(o)
    else: ax.set_title(o)

def show_titled_image(o,ax):
    "Call `show_image` destructuring `o` to `(img,title)`"
    show_image(o[0], ax, title=o[1])

def show_image_batch(b, show=show_titled_image, items=9, cols=3, figsize=None, **kwargs):
    "Display batch `b` in a grid of size `items` with `cols` width"
    rows = (items+cols-1) // cols
    if figsize is None: figsize = (cols*3, rows*3)
    fig,axs = plt.subplots(rows, cols, figsize=figsize)
    for *o,ax in zip(*b, axs.flatten()): show(o, ax=ax, **kwargs)

class Categorize(Transform):
    "Reversible transform of category string to `vocab` id"
    _order=1
    def __init__(self, vocab=None, train_attr="train", subset_idx=None):
        self.vocab,self.train_attr,self.subset_idx = vocab,train_attr,subset_idx
        self.o2i = None if vocab is None else {v:k for k,v in enumerate(vocab)}

    def setup(self, dsrc):
        if self.vocab is not None: return
        if self.subset_idx is not None: dsrc = dsrc.subset(self.subset_idx)
        elif self.train_attr: dsrc = getattr(dsrc,self.train_attr)
        self.vocab,self.o2i = uniqueify(dsrc, sort=True, bidir=True)

    def encodes(self, o): return self.o2i[o] if self.o2i else o
    def decodes(self, o):  return self.vocab[o]
    def shows(self, o, ctx=None): show_title(o, ax=ctx)

def _DataLoader__getattr(self,k):
    try: return getattr(self.dataset, k)
    except AttributeError: raise AttributeError(k) from None
DataLoader.__getattr__ = _DataLoader__getattr

@docs
class TfmDataLoader(GetAttr):
    "Transformed `DataLoader` using a `Pipeline` of `tfms`"
    _xtra = 'batch_size num_workers dataset sampler pin_memory'.split()

    def __init__(self, dataset, tfms=None, batch_size=16, shuffle=False,
                 sampler=None, batch_sampler=None, num_workers=1, **kwargs):
        self.dl = DataLoader(dataset, batch_size, shuffle, sampler, batch_sampler, num_workers=num_workers)
        self.tfm = Pipeline(tfms)
        self.tfm.setup(self)
        self.default = self.dl # for `GetAttr`
        for k,v in kwargs.items(): setattr(self,k,v)

    def __len__(self): return len(self.dl)
    def __iter__(self): return map(self.tfm, self.dl)
    def one_batch(self): return next(iter(self))
    def decode(self, b): return getattr(self.dataset,'decode_batch',noop)(self.tfm.decode(b))

    def show_batch(self, b=None, max_rows=1000, ctxs=None, **kwargs):
        "Show `b` (defaults to `one_batch`), a list of lists of pipeline outputs (i.e. output of a `DataLoader`)"
        if b is None: b=self.one_batch()
        b = self.tfm.decode(b)
        rows = itertools.islice(zip(*L(b)), max_rows)
        if ctxs is None: ctxs = [None] * len(b[0] if is_iter(b[0]) else b)
        for o,ctx in zip(rows,ctxs): self.dataset.show(o, ctx=ctx)

    _docs = dict(decode="Decode `b` using `ds_tfm` and `tfm`",
                 show_batch="Show each item of `b`",
                 one_batch="Grab first batch of `dl`")

@docs
class Cuda(Transform):
    "Move batch to `device` (defaults to `defaults.device`)"
    def __init__(self,device=defaults.device): self.device=device
    def encodes(self, b): return to_device(b, self.device)
    def decodes(self, b): return to_cpu(b)

    _docs=dict(encodes="Move batch to `device`", decodes="Return batch to CPU")

class MaskedTransform(Transform):
    "Abstract class to apply a `Transform` to elements of a collection based on a `mask` (defaults to (True,False))."
    def __init__(self, mask=None, with_lbl=True): self.mask,self.with_lbl = ifnone(mask, (True,False)),with_lbl
    def encodes(self, b): return self._apply(self._encode_one,b)
    def decodes(self, b): return self._apply(self._decode_one,b)

    def _apply(self,f,b):
        if self.with_lbl: return tuple(f(o) if p else o for o,p in zip(b,self.mask))
        return f(b)

@docs
class ByteToFloatTensor(MaskedTransform):
    "Transform image to float tensor, optionally dividing by 255 (e.g. for images)."
    order=20 #Need to run after CUDA if on the GPU
    def __init__(self, div=True, mask=None, with_lbl=True):
        super().__init__(mask, with_lbl)
        self.div = div

    def _encode_one(self, o): return o.float().div_(255.) if self.div else o.float()
    def _decode_one(self, o): return o.clamp(0., 1.) if self.div else o

    _docs=dict(encodes="Convert items matching `mask` to float and optionally divide by 255",
               decodes="Clamp to (0,1) items matching `mask`")

@docs
class Normalize(MaskedTransform):
    "Normalize/denorm batch"
    order=99
    def __init__(self, mean, std, mask=None, with_lbl=True):
        super().__init__(mask, with_lbl)
        self.mean,self.std = mean,std

    def _encode_one(self, x): return (x-self.mean) / self.std
    def _decode_one(self, x):    return (x*self.std ) + self.mean

    _docs=dict(encodes="Normalize batch matching `mask`", decodes="Denormalize batch matching `mask`")

@docs
class DataBunch(GetAttr):
    "Basic wrapper around several `DataLoader`s."
    _xtra = 'one_batch show_batch dataset'.split()

    def __init__(self, *dls): self.dls,self.default = dls,dls[0]
    def __getitem__(self, i): return self.dls[i]

    train_dl,valid_dl = add_props(lambda i,x: x[i])
    train_ds,valid_ds = add_props(lambda i,x: x[i].dataset)

    _docs=dict(__getitem__="Retrieve `DataLoader` at `i` (`0` is training, `1` is validation)",
              train_dl="Training `DataLoader`",
              valid_dl="Validation `DataLoader`",
              train_ds="Training `Dataset`",
              valid_ds="Validation `Dataset`")