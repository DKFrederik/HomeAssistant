#!/bin/sh
ssh homeassistant@192.168.3.10 uptime | grep -ohe 'up .*' | sed 's/,//g' | awk '{ print $2 }'
