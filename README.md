# Smartdoor client system

[![GitHub](https://img.shields.io/github/license/munechika-koyo/cherab_phix)](https://opensource.org/licenses/BSD-3-Clause)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/charliermarsh/ruff)

Smartdoor system including NFC card detecting, key locking/unlocking, turning LED on/off, etc. with Raspberry Pi.

## Quick Installation
```bash
$ git clone https://github.com/munechika-koyo/smartdoor.git
$ cd smartdoor
$ python -m pip install .
```

## Before getting started
Smartdoor Host system which serves the web application for NFC key management must be run. Please
install and deploy it in adavnce. ([see here](https://github.com/munechika-koyo/smartdoor_host)).
