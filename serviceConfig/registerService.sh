#!/bin/sh

# create symbolic links of *.service into /etc/systemd/system dir
DIR=/etc/systemd/system

sudo ln -sf ${PWD}/smartdoor.service ${DIR}/smartdoor.service

# enable & start service
sudo systemctl daemon-reload
sudo systemctl enable smartdoor.service
sudo systemctl start smartdoor.service