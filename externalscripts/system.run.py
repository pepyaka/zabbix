#!/usr/bin/env python

import socket
import struct
import sys
import base64
import os
import bz2


def parse_args():
    port = 10050
    exe_args = ''
    try:
        host = sys.argv[1].split(':')
        exe_path = sys.argv[2]
    except IndexError:
        sys.exit('Usage: system.run.py host[:port] path_to_exec [exec_args]')

    if len(sys.argv) > 3:
        exe_args = '"' + '" "'.join(sys.argv[2:]) + '"'

    if len(host) > 1:
        port = host[1]

    host = host[0]

    return (host, port, exe_path, exe_args)


def system_run(exe_path, exe_args):
    with open(exe_path, 'r') as f:
        exe_content = f.read()
    exe_name = os.path.basename(exe_path)
    exe_bz2 = bz2.compress(exe_content)
    exe_b64 = base64.encodestring(exe_bz2)
    cmd = """
        WD=/tmp/zabbix.system.run; mkdir -p $WD || exit 1
        cd $WD; EXEC="{0}"
        echo "{1}" | base64 -i -d | bzcat > "$EXEC"
        chmod +x "$EXEC" && ./"$EXEC" {2}
    """.format(exe_name, exe_b64, exe_args)

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
    host, port, exe_path, exe_args = parse_args()
    key = system_run(exe_path, exe_args)
    get_data = zabbix_get(host, port, key)
    print get_data


if __name__ == '__main__':
    main()
