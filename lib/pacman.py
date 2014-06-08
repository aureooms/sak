import inspect, lib, importlib, os, types

def reset(t):
	t.__all__ = []

def init(t):
	if type(getattr(t, '__all__', None)) != list:
		reset(t)

def exists(s, t):
	return s in t.__dict__

def public(t, pred = None):
	if pred is None : pred = []

	if len(pred) == 0:
		return (e for e in t.__all__)

	for key in t.__all__:
		for p in pred:
			if p(getattr(t, key)):
				yield key
				break

def setpublic(t, pred = None):
	if pred is None : pred = []
	
	if len(pred) == 0 :
		t.__all__ = t.__dict__.keys()
		return

	publ = set(t.__all__)
	for key, val in t.__dict__.items():
		if key in publ : continue
		for p in pred :
			if p(val):
				publ.add(key)
				break



	t.__all__ = list(publ)

def ispublic(s, t):
	return s in t.__all__


def setprivate(t, pred = None):
	if pred is None : pred = []

	if len(pred) == 0:
		t.__all__ = []
		return


	publ = set(t.__all__)

	for key in t.__all__:
		for p in pred :
			if p(getattr(t, key)):
				publ.remove(key)
				break

	t.__all__ = list(publ)

def isprivate(s, t):
	return exists(s, t) and not ispublic(s, t)


def clean(t):
	publ = set(t.__all__)
	for key in t.__all__:
		try:
			getattr(t, key)
		except AttributeError:
			publ.remove(key)

	t.__all__ = list(publ)


def package(t):
	reset(t)
	setpublic(t, [inspect.ismodule])

def module(t):
	package(t)
	setpublic(t, [inspect.isclass, inspect.isfunction, inspect.isgenerator])

def toolbox(t):
	reset(t)
	setpublic(t, [inspect.isfunction])


def resolve(n, t):

	alter = [
		lambda s : s,
		lambda s : s.lower(),
		lambda s : lib.str.cons(s),
		lambda s : lib.str.cons(s.lower())
	]

	for a in alter:
		s = a(n)

		# MATCH
		l = [x for x in t.__all__ if a(x) == s]
		if len(l) > 0 : return l

		# PREFIX
		l = [x for x in t.__all__ if a(x).startswith(s)]
		if len(l) > 0 : return l

		# SUFFIX
		l = [x for x in t.__all__ if a(x).endswith(s)]
		if len(l) > 0 : return l

		# SUBSTR
		l = [x for x in t.__all__ if s in a(x)]
		if len(l) > 0 : return l

	return []



def __init__(t, root):

	reset(t)

	module = os.path.basename(root)

	for f in os.listdir(root):
		path = root + '/' + f

		if os.path.isdir(path):
			if os.path.isfile(path + '/__init__.py'):
				setattr(t, f, importlib.import_module(module + '.' + f))
				t.__all__.append(f)

			elif f != '__pycache__':
				setattr(t, f, types.ModuleType(f))
				__init__(t, path)

		elif os.path.isfile(path) and f != '__init__.py':
			name, ext = os.path.splitext(f)

			if ext == '.py':
				s = importlib.import_module(module + '.' + name)
				setattr(t, name, s)
				t.__all__.append(name)
				toolbox(s)
