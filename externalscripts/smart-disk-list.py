#!/usr/bin/env python

import socket
import struct
import sys
import json

bash = '''
    scan() {
        D="$1 -d sat"
        if I=$(sudo smartctl -i $D 2>/dev/null) ; then
            M=$(echo "$I" | sed -En "s/Device Model:\s+(.+)/\\1/p")
            if [ -n "$M" ] ; then
                echo "$D # $M"
                return
            fi
        fi
        for i in {0..127} ; do
            D="$1 -d megaraid,$i"
            if I=$(sudo smartctl -i $D 2>/dev/null) ; then
                M=$(echo "$I" | sed -En "s/Product:\s+(.+)/\\1/p")
                [ -n "$M" ] && echo "$D # $M"
            fi
        done
        [ -n "$M" ] && return
        D="$1 -d scsi"
        if I=$(sudo smartctl -i $D 2>/dev/null) ; then
            M=$(echo "$I" | sed -En "s/Product:\s+(.+)\s+$/\\1/p")
            if [ -n "$M" ] ; then
                echo "$D # $M"
                return
            fi
        fi
    }
    cd /sys/bus/scsi/devices
    for sd in [0-9]:[0-9]:[0-9]:[0-9] ; do
        if [ $(cat $sd/type) == 0 ] ; then
            if [ -d $sd/block/sd* ] ; then
                for sb in $sd/block/sd* ; do
                    scan /dev/${sb##*/}
                done
            else
                for sg in $sd/scsi_generic/sg* ; do
                    scan /dev/${sg##*/}
                done
            fi
        fi
    done
'''
bash = bash.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`')


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


def str2packed(data):
    header_field = struct.pack('<4sBQ', 'ZBXD', 1, len(data))
    return header_field + data


def packed2str(packed_data):
    header, version, length = struct.unpack('<4sBQ', packed_data[:13])
    (data, ) = struct.unpack('<%ds' % length,
                             packed_data[13:13+length])
    return data


def zabbix_get(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host[0], host[1]))
    cmd = 'system.run["{0}"]'.format(bash)
    s.sendall(str2packed(cmd))

    data = ''
    while True:
        buff = s.recv(1024)
        if not buff:
            break
        data += buff

    response = packed2str(data)

    s.close()
    return response


def create_lld_json(disk_list):
    disk_list = disk_list.split('\n')
    data = {'data': []}
    for d in disk_list:
        d = d.split('#')
        disk = d[0].split('-d')
        item = {
            '{#DISK}': d[0].strip(),
            '{#PATH}': disk[0].strip(),
            '{#TYPE}': disk[1].strip(),
            '{#NAME}': d[1].strip()
        }
        data['data'].append(item)
    return json.dumps(data, indent=2)


def main():
    try:
        host = sys.argv[1]
    except IndexError:
        sys.exit('Usage: {0} host[:port]'.format(sys.argv[0]))

    host = host.split(':')
    if len(host) == 1:
        host.append(10050)

    disk_list = zabbix_get(host)
    if not disk_list:
        sys.exit("Empty disk list!")

    print disk_list

    data = [{
        'host': host[0],
        'key': 'smart.list',
        'value': create_lld_json(disk_list),
    }]
    s_resp = zabbix_sender(data)
    if s_resp['response'] != 'success':
        print zabbix_sender(data)

if __name__ == '__main__':
    main()
