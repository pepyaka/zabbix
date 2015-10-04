#!/usr/bin/env python

import socket
import struct
import json
import argparse


def parse_args():
    # Defaults
    args = {
        'port': 10050,
        's_port': 10051
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('host',
                        help='Target host and optinally port',
                        metavar='host[:port]',
                        default='localhost:10050')
    parser.add_argument('exec_path',
                        help='Path to executable thing',
                        default='/bin/date')
    parser.add_argument('-v', '--verbosity',
                        help='Increase output verbosity',
                        action='count',
                        default=0)
    parser.add_argument('-z', '--zabbix-server',
                        help='Zabbix server host:port',
                        metavar='server[:port]',
                        default='localhost:10051')
    a = parser.parse_args()

    host = a.host.split(':')
    args['host'] = host[0]
    if len(host) > 1:
        args['port'] = int(host[1])

    zabbix_server = a.zabbix_server.split(':')
    args['server'] = zabbix_server[0]
    if len(zabbix_server) > 1:
        args['s_port'] = int(zabbix_server[1])

    return args


# Thanks to Takanori Suzuki
# https://github.com/BlueSkyDetector/code-snippet/tree/master/ZabbixSender
def zabbix_sender(sender_data, server='localhost', port=10051):
    # Zabbix header and version
    zbx_header = 'ZBXD'
    zbx_version = 1
    # Encode JSON and binary structure of data
    zbx_sender_data = {'request': 'sender data', 'data': sender_data}
    zbx_sender_json = json.dumps(zbx_sender_data, separators=(',', ':'))
    json_byte = len(zbx_sender_json)
    send_data = struct.pack("<4sBq" + str(json_byte) + "s",
                            zbx_header, zbx_version,
                            json_byte, zbx_sender_json)
    # Connect to server
    so = socket.socket()
    so.connect((server, port))
    # Sent data to server
    wobj = so.makefile('wb')
    wobj.write(send_data)
    wobj.close()
    # Recieve response
    robj = so.makefile('rb')
    recv_data = robj.read()
    robj.close()
    so.close()
    # Pick data from binary response
    struct_str = str(len(recv_data) - struct.calcsize("<4sBq"))
    r_data = struct.unpack("<4sBq" + struct_str + "s", recv_data)
    recv_json = json.loads(r_data[3])
    # Return server response
    return recv_json


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
    r_header, r_version, r_length = struct.unpack('<4sBQ', r_data[:13])
    (response, ) = struct.unpack('<%ds' % r_length, r_data[13:13 + r_length])

    c.close()

    return response


def main():
    args = parse_args()
    get_data = zabbix_get(args['host'], args['port'])
    print get_data
    send_data = {
        'host': args['host'],
        'key': 'agent.hostname',
        'value': get_data
    }
    zs_response = zabbix_sender(send_data, args['server'], args['s_port'])
    print zs_response


if __name__ == '__main__':
    main()
