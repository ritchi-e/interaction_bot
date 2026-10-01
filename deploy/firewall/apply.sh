#!/bin/bash
# Host firewall for the app VM.
# 80/TCP is public so Let's Encrypt can validate hostnames.
# 443/TCP is public (dashboard and WhatsApp webhooks).
# 3010/TCP is public for the Dograh UI.
# Oracle's image rejects all other new input before ufw, so these rules
# are inserted immediately ahead of that reject.
set -euo pipefail

CIDR_FILE="${CIDR_FILE:-/etc/caller-firewall/meta-as32934.cidr}"
SET=meta-sip

if [[ ! -f "$CIDR_FILE" ]]; then
  echo "missing $CIDR_FILE" >&2
  exit 1
fi

ipset create "$SET" hash:net family inet hashsize 64 maxelem 256 -exist
ipset flush "$SET"
while read -r prefix; do
  [[ -z "$prefix" || "$prefix" == \#* ]] && continue
  ipset add "$SET" "$prefix"
done < "$CIDR_FILE"

ensure() {
  local comment="$1"
  shift
  if iptables -C INPUT -m comment --comment "$comment" "$@" 2>/dev/null; then
    return
  fi
  local line
  line="$(iptables -L INPUT -n --line-numbers | awk 'NR>2 && $2=="REJECT" {print $1; exit}')"
  if [[ -n "$line" ]]; then
    iptables -I INPUT "$line" -m comment --comment "$comment" "$@"
  else
    iptables -A INPUT -m comment --comment "$comment" "$@"
  fi
}

drop_rule() {
  local comment="$1"
  shift
  while iptables -C INPUT -m comment --comment "$comment" "$@" 2>/dev/null; do
    iptables -D INPUT -m comment --comment "$comment" "$@"
  done
}

ensure caller-http -p tcp --dport 80 -j ACCEPT
ensure caller-https -p tcp --dport 443 -j ACCEPT
ensure caller-dograh-ui -p tcp --dport 3010 -j ACCEPT
drop_rule caller-sip -p tcp --dport 5061 -m set --match-set "$SET" src -j ACCEPT
drop_rule caller-rtp -p udp --dport 10000:20000 -m set --match-set "$SET" src -j ACCEPT
