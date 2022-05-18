#!/bin/sh

# copy smartdoor.service into systemd/system dir
sudo cp -a smartdoor.service /etc/systemd/system

# start & enable service
sudo systemctl daemon-reload
sudo systemctl start smartdoor
sudo systemctl enable smartdoor
