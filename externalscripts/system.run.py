#!/usr/bin/env python

import socket
import struct
import sys
import base64
import os
import bz2
import argparse
import hashlib

verbosity = 0
exe_dir = '/var/tmp/zabbix/system.run'


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-H', '--host',
                        help='Target host',
                        default='localhost')
    parser.add_argument('-P', '--port',
                        help='Target port',
                        type=int,
                        default=10050)
    parser.add_argument('exec_path',
                        help='Path to executable thing')
    parser.add_argument('exec_args',
                        nargs='*',
                        help='Args for executable')
    parser.add_argument('-v', '--verbosity',
                        help='Increase output verbosity',
                        action='count',
                        default=0)
    args = parser.parse_args()

    return args


def check_exe_md5(exe_path):
    try:
        with open(exe_path, 'rb') as f:
            exe_content = f.read()
    except IOError:
        sys.exit('Can\'t open file {0} for reading'.format(exe_path))

    exe_md5 = hashlib.md5(exe_content).hexdigest()

    return (exe_content, exe_md5)


def system_run(exe_name, exe_content, exe_args):
    exe_bz2 = bz2.compress(exe_content)
    exe_b64 = base64.encodestring(exe_bz2)
    if verbosity > 0:
        print 'Exec length: {0}'.format(len(exe_content))
        print 'Bzipped exec length: {0}'.format(len(exe_bz2))
        print 'Bzipped Base64 exec length: {0}'.format(len(exe_b64))
    cmd = """
        WD={0}; mkdir -p $WD || exit 1
        cd $WD; EXEC="{1}"
        echo "{2}" | base64 -i -d | bzcat > "$EXEC"
        chmod +x "$EXEC" && ./"$EXEC" {3}
    """.format(exe_dir, exe_name, exe_b64, exe_args)

    s = 'system.run[{0}]'.format(cmd)
    return s


def zabbix_get(host='localhost', port=10050, key='agent.hostname'):
    s_data = struct.pack('<4sBQ', 'ZBXD', 1, len(key)) + key

    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.connect((host, port))
    c.sendall(s_data)

    r_data = ''
    while True:
        buff = c.recv(1024)
        if not buff:
            break
        r_data += buff
    try:
        r_header, r_version, r_length = struct.unpack('<4sBQ', r_data[:13])
        r_struct = struct.unpack('<%ds' % r_length, r_data[13:13 + r_length])
    except struct.error:
        sys.exit('No answer from zabbix-agent')

    c.close()

    return r_struct[0]


def main():
    global verbosity
    args = parse_args()
    verbosity = args.verbosity
    if verbosity > 0:
        print 'ARGS: {0}'.format(args)
    exe_name = os.path.basename(args.exec_path)
    exe_args = '"' + '" "'.join(args.exec_args) + '"'
    exe_content, exe_md5 = check_exe_md5(args.exec_path)
    vfs_md5_key = 'vfs.file.md5sum[{0}/{1}]'.format(exe_dir, exe_name)
    vfs_md5 = zabbix_get(args.host, args.port, vfs_md5_key)
    if verbosity > 0:
        print 'Exec name: {0}'.format(exe_name)
        print 'Exec args: {0}'.format(exe_args)
        print 'Local  exec MD5SUM: {0}'.format(exe_md5)
        print 'Remote exec MD5SUM: {0}'.format(vfs_md5)

    if exe_md5 == vfs_md5:
        if verbosity > 0:
            print 'Exec already exec, just run it'
        vfs_key = 'system.run[{0}/{1} {2}]'.format(exe_dir, exe_name, exe_args)
        get_data = zabbix_get(args.host, args.port, vfs_key)
    else:
        if verbosity > 0:
            print 'Copy exec content to host'
        key = system_run(exe_name, exe_content, exe_args)
        get_data = zabbix_get(args.host, args.port, key)
    print get_data


if __name__ == '__main__':
    main()
