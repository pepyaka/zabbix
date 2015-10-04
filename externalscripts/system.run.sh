#!/bin/bash

HOST="$1"
CMD="$2"
shift
shift

BASE64=$(base64 "$CMD")
CMDNAME=$(basename "$CMD")

COMMAND='
WORKDIR=/tmp/zabbix.system.run
mkdir -p $WORKDIR || exit 1
cd $WORKDIR
EXEC="'$CMDNAME'"
echo "'$BASE64'" | base64 -i -d > "$EXEC"
chmod +x "$EXEC"
./"$EXEC" '"$@"'
'

zabbix_get -s "$HOST" -k 'system.run['"$COMMAND"']'
