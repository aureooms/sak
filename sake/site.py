import json, os, base64, tempfile, hashlib, lib, socket


def down(directory = '.', config_file = 'json/config.json', dry_run = False):
	local = {'root' : os.path.abspath(directory)}

	pre = lambda *x: None

	def callback(helper, config):
		helper.server_down(config, local)

	if not _helper.check_local_root(local['root']) : return
	_helper.wrap(local, config_file, dry_run, pre, callback)

def up(directory = '.', config_file = 'json/config.json', dry_run = False):
	local = {'root' : os.path.abspath(directory)}

	pre = lambda *x: None

	def callback(helper, config):
		helper.server_up(config, local)

	if not _helper.check_local_root(local['root']) : return
	_helper.wrap(local, config_file, dry_run, pre, callback)


def diff(directory = '.', config_file = 'json/config.json'):
	return push(directory, config_file, dry_run = True)


def push(directory = '.', config_file = 'json/config.json', dry_run = False):

	local = {
		'root' : os.path.abspath(directory),
		'hash' : {},
		'tree' : {}
	}

	def pre(helper, config):
		helper.local_fetch(local['root'], config, local['hash'], local['tree'])

	def callback(helper, config):

		server = {
			'root' : config['root'],
			'hash' : {},
			'tree' : {}
		}

		helper.server_fetch(config, server)
		helper.update(config, local, server)

	if not _helper.check_local_root(local['root']) : return
	_helper.wrap(local, config_file, dry_run, pre, callback)


def hash(directory = '.', config_file = 'json/config.json'):
	local = {'root' : os.path.abspath(directory)}
	dry_run = False
	pre = lambda *args, **kwargs : None

	def callback(helper, config):

		server = {
			'hash' : {},
			'tree' : {}
		}

		helper.server_hash(config, server['hash'], server['tree'])
		helper.send_hash(config, server)

	_helper.wrap(local, config_file, dry_run, pre, callback)




class _helper(object):

	default = {
		"host" : "hostaddr",
		"username" : "username",
		"root"   : "www",

		"index"  : ".hash",
		"online" : ".online",

		"down"   : ".htaccess",
		"up"     : ".htaccess",
		
		"tree"   : {},
		"ignore" : []
	}

	def __init__(self, dry_run):
		self.do = not dry_run
		self.ftp = None
		self.remote = None

	def setFTP(self, ftp):
		self.ftp = ftp
		self.remote = lib.nice.ftp.FTP(ftp, self.do)

	def check_local_root(root):
		if not os.path.isdir(root):
			print("[Errno 1] Local root '%s' not found" % root)
			return False

		else:
			return True

	def wrap(local, config_file, dry_run, pre, callback):

		try:
			config = _helper.default.copy()
			with open(os.path.join(local['root'], config_file), 'r') as f:
				config.update(json.load(f))

		except FileNotFoundError as e:
			print(e)
			return

		helper = _helper(dry_run)

		pre(helper, config)

		with lib.ftp.FTP() as ftp:
			helper.setFTP(ftp)

			try:
				ftp.loginprompt(config)
				callback(helper, config)

			except socket.gaierror as e:
				print(e)



	def local_file(self, config, hash_t, tree_i, tree, dir_list, item, minipath, path):
		base, ext = os.path.splitext(minipath)
		if ext == config['online'] :
			if os.path.basename(minipath) in tree : return
			else : dest = base
		elif item + config['online'] in dir_list :
			dest = minipath
			path += config['online']
			minipath += config['online']
		else : dest = minipath
		h_ascii = lib.nice.file.hascii(path)
		hash_t.setdefault(h_ascii, {'s' : [], 'd' : []})
		hash_t[h_ascii]['s'].append(minipath)
		hash_t[h_ascii]['d'].append(dest)
		tree_i[item] = [h_ascii, dest]

	def local_fetch(self, root, config, hash_t, tree_i, current = '', tree = None):
		if tree is None : tree = config['tree']
		dir_list = os.listdir(root + '/' + current)
		for item, what in tree.items():
			minipath = current + item
			path = root + '/' + minipath
			if os.path.isfile(path):
				self.local_file(config, hash_t, tree_i, tree, dir_list, item, minipath, path)

			elif os.path.isdir(path):
				if what is None : what = { sub : None for sub in os.listdir(path)}
				tree_i[item] = {}
				self.local_fetch(root, config, hash_t, tree_i[item], current + item + '/', what)


	def server_fetch(self, config, server):
		index_file = '/%s/%s' % (config['root'], config['index'])
		if self.ftp.isfile(index_file):
			chuncks = []
			self.ftp.retrlines('RETR %s' % index_file, chuncks.append)
			index = ''.join(chuncks)
			data = json.loads(index)
			server['hash'] = data['hash']
			server['tree'] = data['tree']


	def ensure_structure_rec(self, config, local_h, current):
		for item, data in local_h.items():
			if type(data) == dict:
				self.remote.mkd('/%s/%s%s' % (config['root'], current, item))
				self.ensure_structure_rec(config, local_h[item], current + item + '/')

	def ensure_structure(self, config, local_h, server_h, current = ''):

		for item, data in local_h.items():
			if type(data) == dict:
				if item not in server_h:
					self.remote.mkd('/%s/%s%s' % (config['root'], current, item))
					self.ensure_structure_rec(config, local_h[item], current + item + '/')
				else:
					self.ensure_structure(config, local_h[item], server_h[item], current + item + '/')


	def clean(self, config, subtree, current):
		for item, data in subtree.items():
			if type(data) == dict : self.clean(config, data, current + '/' + item)

		self.remote.rmd('/%s/%s' % (config['root'], current))


	def clean_structure(self, config, local_h, server_h, current = ''):

		for item, data in server_h.items():
			if type(data) == dict:
				if item not in local_h:
					self.clean(config, data, current + item)
				else:	
					self.clean_structure(config, local_h[item], server_h[item], current + item + '/')



	def delete_minipaths(self, minipaths, root):
		for minipath in minipaths:
			self.remote.delete('/%s/%s' % (root, minipath))


	def update_moved(self, config, local, h, not_handled, minipaths):	
		for minipath in minipaths:

			# moved files
			if minipath not in local['hash'][h]['d']:
				if len(not_handled) > 0:
					replace = not_handled[0]
					del not_handled[0]

					self.remote.rename('/%s/%s' % (config['root'], minipath), '/%s/%s' % (config['root'], replace))
				else:
					self.remote.delete('/%s/%s' % (config['root'], minipath))

			# not moved
			else:
				pass

	def update_copied(self, config, local, h, not_handled):
		base = local['hash'][h]['s'][0]
		with open('%s/%s' % (local['root'], base), 'rb') as f:
			for i in range(len(not_handled)):
				f.seek(0)
				self.remote.storbinary('/%s/%s' % (config['root'], not_handled[i]), f)

	def update_moved_copied_minipaths(self, config, local, h, minipaths):
		not_handled = [x for x in local['hash'][h]['d'] if x not in minipaths]

		self.update_moved(config, local, h, not_handled, minipaths)

		if len(not_handled) > 0 : self.update_copied(config, local, h, not_handled)
		

	def update_deleted_moved_copied(self, config, local, server):
		for h, minipaths in server['hash'].items():

			# deleted files
			if h not in local['hash']:
				self.delete_minipaths(minipaths, config['root'])

			else:
				self.update_moved_copied_minipaths(config, local, h, minipaths)

	def add_paths(self, config, local, paths):
		for i in range(len(paths['s'])):
			with open('%s/%s' % (local['root'], paths['s'][i]), 'rb') as f:
				self.remote.storbinary('/%s/%s' % (config['root'], paths['d'][i]), f)

	def update_added(self, config, local, server):
		for h, paths in local['hash'].items():
			# added files
			if h not in server['hash']:
				self.add_paths(config, local, paths)




	def rec_build(local_t, server_t):
		for item, value in local_t.items():
			if type(value) == list:
				server_t[item] = value[0]
			elif type(value) == dict:
				server_t[item] = {}
				_helper.rec_build(value, server_t[item])

	def update_index(self, config, local):
		data = {
			'hash' : {},
			'tree' : {}
		}

		for key in local['hash']:
			data['hash'][key] = local['hash'][key]['d']


		_helper.rec_build(local['tree'], data['tree'])


		with open('%s/%s' % (local['root'], config['index']), 'w') as f:
			json.dump(data, f, indent = '\t')

		with open('%s/%s' % (local['root'], config['index']), 'rb') as f:
			self.remote.storbinary('/%s/%s' % (config['root'], config['index']), f)
			self.remote.chmod('640', '/%s/%s' % (config['root'], config['index']))

	def update(self, config, local, server):
		self.ensure_structure(config, local['tree'], server['tree'])
		self.update_deleted_moved_copied(config, local, server)
		self.update_added(config, local, server)
		self.update_index(config, local)
		self.clean_structure(config, local['tree'], server['tree'])


	def remote_file_ascii_hash(self, config, minipath):
		return self.remote.hascii('/%s/%s' % (config['root'], minipath))

	def filter_item(self, item, index):
		return item == '.' or item == '..' or item == index

	def server_hash(self, config, hash_t, tree, current = ''):
		for t, item in self.ftp.ls(current):

			print('%s%s' % (current, item))
			if self.filter_item(item, config['index']) : continue

			minipath = current + item
			if minipath in config['ignore'] : continue

			if t == self.ftp.FILE:
				h_ascii = self.remote_file_ascii_hash(config, minipath)
				print(h_ascii)
				hash_t.setdefault(h_ascii, [])
				hash_t[h_ascii].append(minipath)
				tree[item] = h_ascii

			elif t == self.ftp.DIR:
				tree[item] = {}
				self.server_hash(config, hash_t, tree[item], current + item + '/')

	def send_hash(self, config, data):
		with tempfile.NamedTemporaryFile('w', delete = False) as tmp:
			json.dump(data, tmp, indent = '\t')

		with open(tmp.name, 'rb') as f:
			self.remote.storbinary('/%s/%s' % (config['root'], config['index']), f)

		os.remove(tmp.name)

		self.remote.chmod('640', '/%s/%s' % (config['root'], config['index']))



	def server_down(self, config, local):
		return self.server_switch(config, local, 'down')



	def server_up(self, config, local):
		return self.server_switch(config, local, 'up')


	def server_switch(self, config, local, which):
		src = os.path.join(local['root'], config[which])
		if os.path.isfile('%s%s' % (src, config['online'])) : src += config['online']

		with open(src, 'rb') as f:
			self.remote.storbinary('/%s/%s' % (config['root'], config['up']), f)

