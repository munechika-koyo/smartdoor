#!/bin/sh

# create symbolic links of *.service into /etc/systemd/system dir
DIR=/etc/systemd/system

sudo ln -sf ${PWD}/smartdoor.service ${DIR}/smartdoor.service
sudo ln -sf ${PWD}/smartdoor_restart.service  ${DIR}/smartdoor_restart.service
sudo ln -sf ${PWD}/smartdoor_restart.timer ${DIR}/smartdoor_restart.timer

# enable & start service
sudo systemctl daemon-reload
sudo systemctl enable smartdoor.service
sudo systemctl enable smartdoor_restart.service
sudo systemctl enable smartdoor_restart.timer
sudo systemctl start smartdoor.service
sudo systemctl start smartdoor_restart.timer
