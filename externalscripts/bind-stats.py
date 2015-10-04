#!/usr/bin/python

import sys
import urllib2
import xmltodict
import json
import struct
import socket


def parse_args():
    dflt_port = 8053
    try:
        host = sys.argv[1]
    except IndexError:
        sys.exit('Usage: {0} host[:port]'.format(sys.argv[0]))

    host = host.split(':')
    if len(host) == 1:
        host.append(dflt_port)
    return tuple(host)


def parse_xml(xml):
    doc = xmltodict.parse(xml)
    return doc['isc']['bind']['statistics']


def map_in_qr(in_qr):
    return {
        'key': 'bind.stats.server[InQueries, {0}]'.format(in_qr['name']),
        'value': int(in_qr['counter'])
    }


def map_memory(k, v):
    return {
        'key': 'bind.stats.memory[Summary, {0}]'.format(k),
        'value': int(v)
    }


# Thanks to Takanori Suzuki
# https://github.com/BlueSkyDetector/code-snippet/tree/master/ZabbixSender
def zabbix_sender(sender_data):
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
    so.connect(('127.0.0.1', 10051))
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
    tmp_data = struct.unpack("<4sBq" + struct_str + "s", recv_data)
    recv_json = json.loads(tmp_data[3])
    # Return server response
    return recv_json


def main():
    host, port = parse_args()
    try:
        stats = urllib2.urlopen('http://{0}:{1}'.format(host, port))
    except IOError as e:
        sys.exit(e)
    stats = parse_xml(stats.read())
    #print(json.dumps(stats['memory']['summary'], indent=2))

    summary = stats['memory']['summary']
    rdtype = stats['server']['queries-in']['rdtype']
    data = []
    data += [map_memory(k, v) for k, v in summary.iteritems()]
    data += [map_in_qr(d) for d in rdtype]

    # add host elemnt for every item
    for d in data:
        d.update({'host': host})
    print(json.dumps(data, indent=2))

    # Send data to zabbix server
    s_resp = zabbix_sender(data)
    print s_resp
    if s_resp['response'] != 'success':
        print s_resp


if __name__ == '__main__':
    main()
