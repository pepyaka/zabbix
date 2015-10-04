#!/bin/bash

HOST="$1"

if [ "$HOST" == "" ] ; then
    echo "No host argument!" >&2
    exit 1
fi

declare -A CMD=(
    [Baseboard serial]='system.run[
        sudo /usr/sbin/dmidecode -s baseboard-serial-number
    ]'
    [Chassis/System serial]='system.run[
        cmd="sudo dmidecode -s "
        c=$(${cmd}chassis-serial-number)
        s=$(${cmd}system-serial-number)
        echo "$c / $s"
    ]'
    [BIOS Tag]='system.run[
        sudo /usr/sbin/dmidecode -s baseboard-asset-tag
    ]'
    [Chassis Tag]='system.run[
        sudo /usr/sbin/dmidecode -s chassis-asset-tag
    ]'
    [HW MAC Address]='system.run[
        for f in /sys/class/net/*; do
            readlink $f | grep -qv virtual && echo "$(cat $f/address) "
        done
    ]'
    [Hardware]='system.run[
        cmd="sudo dmidecode -s baseboard-"
        m=$(${cmd}manufacturer)
        v=$(${cmd}version)
        n=$(${cmd}product-name)
        echo "$n - $v ($m)"
    ]'
    [CPU]="system.run[
        sed -En 's/model\sname\s:\s//p' /proc/cpuinfo | uniq -c | sed -E 's/\s+([0-9]+)\s+(.+)/\1 x \2/'
    ]"
    [Memory]='system.run[
        (IFS=": "; sudo dmidecode -qt 17|\
        while read k v; do
            if [ "$k" != "" ]; then
                eval ${k//[[:space:]]/}=\"$v\"
            else
                echo "$Size ($Speed)"
            fi
        done)\
        | sort | uniq -c | sed -E "s/\s+([0-9]+)\s+(.+)/\1 x \2/"

    ]'
    [Hardware (Full details)]='system.run[
        echo "#### CPU"
        awk -F: "\$0 ~ /model name/ {print \$2}" /proc/cpuinfo\
        | uniq -c | sed "s/\\s\+\([0-9]\)\\s\+\(.*\)/- \1 x \"\2\"/"
        echo "#### Memory"
        (IFS=": "; sudo dmidecode -qt 17|\
        while read k v; do
            if [ "$k" != "" ]; then
                eval ${k//[[:space:]]/}=\"$v\"
            else
                echo "$Size ($Speed)"
            fi
        done)\
        | sort | uniq -c | sed "s/\\s\+\([0-9]\)\\s\+\(.*\)/- \1 x \"\2\"/"

    ]'
    [Chassis]='system.run[
        cmd="sudo dmidecode -s chassis-"
        m=$(${cmd}manufacturer)
        v=$(${cmd}version)
        s=$(${cmd}serial-number)
        echo "$v ($m) SN: $s"
    ]'
    [Default gateway]="system.run[
        ip ro | awk '\$1 == \"default\" {print \$3}'
    ]"
    [SMBIOS]='system.run[
        sudo dmidecode -q -t0 -t1 -t2 -t3\
        | sed -rn -e "s/^(\w)/#### \1/p" -e "s/^\t(\w)/- \1/p"
    ]'
    [IPMI IP address]="system.run[
        sudo ipmiutil lan -rc | sed -n 's/^Channel 1 IP address\s\+| \(.\+\)/\1/p'
    ]"
    [IPMI default gateway]="system.run[
        sudo ipmiutil lan -rc | sed -n 's/^Channel 1 Def gateway IP\s\+| \(.\+\)/\1/p'
    ]"
    [IPMI netmask]="system.run[
        sudo ipmiutil lan -rc | sed -n 's/^Channel 1 Subnet mask\s\+| \(.\+\)/\1/p'
    ]"
)

declare -A RESULTS

for K in "${!CMD[@]}"; do
    RESULTS["$K"]=$(/usr/bin/zabbix_get -s "${HOST}" -k "${CMD[$K]}")
done

RESULTS["Hardware (Full details)"]=$(
    echo "#### Memory"
    echo "${RESULTS[Memory]}" | sed "s/^/- /"
    echo "#### CPU"
    echo "${RESULTS[CPU]}" | sed "s/^/- /"
)

ECHO_LIST=(
    'SMBIOS'
)
for K in "${ECHO_LIST[@]}" ; do
    echo "${RESULTS[$K]}"
    echo
done

SENDER_LIST=(
    'Baseboard serial'
    'Chassis/System serial'
    'BIOS Tag'
    'Chassis Tag'
    'HW MAC Address'
    'Hardware'
    'Hardware (Full details)'
    'Chassis'
    'Default gateway'
    'SMBIOS'
    'CPU'
    'Memory'
    'IPMI IP address'
    'IPMI default gateway'
    'IPMI netmask'
)
for K in "${SENDER_LIST[@]}" ; do
    SENDER_OUTPUT=$(/usr/bin/zabbix_sender -z 127.0.0.1 -s "${HOST}" -k inventory["$K"] -o "${RESULTS[$K]}" 2>&1)
    SENDER_RETVAL=$?
    if [ $SENDER_RETVAL != 0 ] ; then
        echo "*Error*"
        echo "$K"
        echo "Zabbix sender output:"
        echo "$SENDER_OUTPUT" | sed 's/^/> /'
    fi
done

