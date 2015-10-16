#!/bin/bash

############################## Defaults #####################################
EVENT_ID="{EVENT_ID}"
ITEM_NAME="{ITEM.NAME}"
ITEM_VALUE="{ITEM.VALUE}"
TRIGGER_STATUS="{TRIGGER.STATUS}"
TRIGGER_NAME="{TRIGGER.NAME}"
TRIGGER_SEVERITY="{TRIGGER.SEVERITY}"
TRIGGER_DESCRIPTION="{TRIGGER.DESCRIPTION}"
TRIGGER_ID="{TRIGGER_ID}"
HOST_NAME="{HOST.HOST}"
ZABBIX_HOSTNAME="{\$ZABBIX.HOSTNAME}"
#############################################################################

TO=$1
SUBJECT=$2
BODY=$3
DIRNAME=$(dirname $0)

. <(echo "$BODY" | tr -d '\r')

eval "cat <<EOF
To: $TO
Content-Type: text/html; charset=UTF-8
Subject: $SUBJECT

$(<$DIRNAME/mail.html)
EOF
" | /usr/sbin/sendmail -t
