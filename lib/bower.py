from __future__ import absolute_import, division, print_function, unicode_literals

import lib.sys

BOWER_CMD = "bower"

def runcmd(*args, force = False):
	cmd = []
	cmd.append(BOWER_CMD)
	if force : cmd.append("--force")
	cmd.extend(args)
	lib.sys.call(cmd, stddefault = None)


def register(bowername, gitendpoint, force = False):
	runcmd("register", bowername, "git://%s.git" % gitendpoint, force = force)

def unregister(bowername, force = False):
	runcmd("unregister", bowername, force = force)