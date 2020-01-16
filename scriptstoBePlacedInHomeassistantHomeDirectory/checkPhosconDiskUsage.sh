#!/bin/sh
ssh homeassistant@192.168.3.10 "df -lh --output=used / | tail -n 1"
