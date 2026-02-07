import re
import shlex
import os
import tempfile
import marshal
import logging as log
import shutil
from subprocess import Popen, PIPE, check_output
from functools import cache
from getpass import getuser
from socket import gethostname
from pprint import pp

PY3 = True                      # dropped PY2 support

class P4CLI(object):
    """Poor mans's implementation of P4Python using P4
    CLI... just enough to support p4review2.py.

    """

    charset = None              # P4CHARSET
    encoding = "utf8"           # default encoding
    input = None                # command input

    array_key_regex = re.compile(r"^(\D*)(\d*)$") # depotFile0, depotFile1...

    def __init__(self, p4bin=None, port=None, user=None, client=None):
        self.p4bin = p4bin or shutil.which('p4')
        if not self.p4bin:
            raise RuntimeError("P4CLI exception - 'p4' command not found in PATH.")
        self.user = user or self.env("P4USER")
        self.port = port or self.env("P4PORT")
        self.client = client or self.env("P4CLIENT")
        if self.env("P4CHARSET") == "none":
            self.charset = None  # you *can* have "P4CHARSET=none" in your config...
        self.tempfiles = []

    def __repr__(self):
        return "<P4CLI({u}@{c} on {p})>".format(u=self.user, c=self.client, p=self.port)

    def __del__(self):
        """cleanup """
        for f in self.tempfiles:
            os.unlink(f)

    def __getattr__(self, name):
        if name.startswith("run"):
            p4cmd = None
            if name.startswith("run_"):
                p4cmd = name[4:]

            def p4runproxy(*args):  # stubs for run_*() functions
                cmd = self.p4pipe
                if p4cmd:  # command is in the argument for calls to run()
                    cmd += [p4cmd]
                if type(args) is tuple or type(args) is list:
                    for arg in args:
                        if type(arg) is list:
                            cmd.extend(arg)
                        else:
                            cmd.append(arg)
                else:
                    cmd += [args]
                cmd = [str(x) for x in cmd]

                if self.input:
                    tmpfd, tmpfname = tempfile.mkstemp()
                    self.tempfiles.append(tmpfname)
                    fd = open(tmpfname, "rb+")
                    marshal.dump(self.input, fd, 0)
                    fd.seek(0)
                    p = Popen(cmd, stdin=fd, stdout=PIPE)
                else:
                    p = Popen(cmd, stdout=PIPE)

                rv = []
                while 1:
                    try:
                        rv.append(marshal.load(p.stdout))
                    except EOFError:
                        break
                    except Exception:
                        log.error("Unknown error while demarshaling data from server.")
                        log.error(" ".join(cmd))
                        break
                p.stdout.close()
                # log.debug(pformat(rv)) # raw data b4 decoding
                self.input = None  # clear any inputs after each p4 command

                rv2 = []  # actual array that we will return
                # magic to turn 'fieldNNN' into an array with key 'field'
                for r in rv:  # rv is a list if dictionaries
                    r2 = {}
                    # fields_needing_sorting = set()
                    for key in r:
                        decoded_key = key
                        if PY3 and type(decoded_key) is bytes:
                            decoded_key = decoded_key.decode(self.encoding)
                        val = r[key]
                        if PY3 and type(val) is bytes:
                            val = val.decode(self.charset or self.encoding or "utf8")
                        regexmatch = self.array_key_regex.match(decoded_key)
                        if not regexmatch:  # re.match may return None
                            continue
                        k, num = regexmatch.groups()

                        if num:  # key in 'filedNNN' form.
                            v = r2.get(k, [])
                            if type(v) is str:
                                v = [v]
                            v.append(val)
                            r2[k] = v
                        else:
                            r2[k] = val
                    rv2.append(r2)
                # log.debug(pformat(rv2)) # data after decoding
                return rv2

            return p4runproxy
        elif name in "connect disconnect".split():
            return self.noop
        elif name in "p4pipe".split():
            cmd = [self.p4bin] + shlex.split(
                f'-G -p "{self.port}" -u {self.user} -c {self.client}'
            )
            if self.charset:
                cmd += ["-C", self.charset]
            return cmd
        else:
            raise AttributeError("'P4CLI' object has no attribute '{}'".format(name))

    def identify(self):
        return f"P4CLI, using {self.p4bin}. P4PORT={self.port}, P4USER={self.user}, P4CLIENT={self.client}."

    def connected(self):
        return True

    def run_login(self, *args):
        cmd = self.p4pipe + ["login"]
        if "-s" in args:
            cmd += ["-s"]
            proc = Popen(cmd, stdout=PIPE)
            out = proc.communicate()[0]
            if marshal.loads(out).get("code") == "error":
                raise Exception("P4CLI exception - not logged in.")
        else:
            proc = Popen(cmd, stdin=PIPE, stdout=PIPE)
            out = proc.communicate(input=self.password)[0]
            out = "\n".join(out.splitlines()[1:])  # Skip the password prompt...
        return [marshal.loads(out)]

    @cache
    def env(self, key: str) -> str:
        set_output = check_output([self.p4bin, "set", key]).decode("utf8")
        val = None
        if set_output:
            val = set_output.split()[0].split("=")[-1]
        if not val:
            if key == "P4USER":
                val = getuser()
            elif key == "P4CLIENT":
                val = gethostname()
            elif key == "P4PORT":
                val = "perforce:1666"
        return val

    def noop(*args, **kws):
        pass                    # stub for methods that has no equivalent in cli

    def run_plaintext(self, *args):
        """Run P4 commands normally and return the outputs in plaintext"""
        cmd = shlex.split(
            """{bin} -p "{p4port}" -u {p4user} -c {p4client}""".format(
                bin=self.p4bin, p4port=self.port, p4user=self.user, p4client=self.client
            )
        ) + list(args)
        rv = check_output(cmd)
        if PY3 and type(rv) is bytes:
            rv = rv.decode(self.charset or self.encoding or "utf8")
        return rv


if __name__ == '__main__':
    p4 = P4CLI()
    pp(p4.identify())
    pp(p4.run_info())
