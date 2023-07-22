"""Smartdoor system including NFC card detecting, key locking/unlocking, turning LED on/off, etc.

This system is designed to be used with Raspberry Pi.

Some CLIs including main sequence is implemented here.
"""
from __future__ import annotations

import subprocess
from logging import config as log_config
from logging import getLogger
from pathlib import Path
from pprint import pformat

import rich_click as click

# Define logger before importing SmartDoor class to follow the same configuration
log_config.fileConfig(Path(__file__).parent / "logging.conf")
logger = getLogger("main")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .smartdoor import SmartDoor

__version__ = "2.0.0.dev1"
__all__ = ["SmartDoor"]


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__, "-V", "--version")
def cli():
    """Smartdoor system CLI."""
    pass


@cli.command()
@click.option(
    "--locked/--unlocked", default=True, show_default=True, help="Set initial key status."
)
def start(locked: bool):
    """Start SmartDoor system.

    The infinite loop workflow is executed at foreground. The initial key status can be set by
    `--locked` or `--unlocked` option, by default `--locked`.

    If you want to stop this system, press Ctrl+C.
    """
    # Instantiate SmartDoor
    logger.info("start smartdoor system")
    door = SmartDoor()

    # Set initial key status
    door.locked = locked
    logger.info("Set initial key status to %s", "locked" if locked else "unlocked")

    # SmartDoor seaquence starts
    try:
        while True:
            tag = door.wait_for_touched()

            # If buttom is pushed
            if tag is None:
                door.led_button.blink(on_time=0.2, off_time=0.2)
                door.door_sequence(user="Button pusher")
                door.led_button.on()
                continue

            # If NFC card is detected
            elif bool(tag):
                user = door.authenticate(tag)

                # If invalid user is detected
                if user is None:
                    door.warning_sequence()
                    continue
                else:
                    door.door_sequence(user=user)

            # If tag == False (KeyboardInterrupt)
            else:
                raise KeyboardInterrupt
    except KeyboardInterrupt:
        logger.info("Smartdoor system stopped by user")

    except Exception:
        logger.exception("unexpected error occurred")
        door.error_sequence()

    finally:
        door.close()


@cli.command()
@click.option("--debug", "-d", is_flag=True, help="show debug log")
def show_log(debug: bool):
    """Show logs of SmartDoor system.

    logs are stored in `~/smartdoor.log` or `~/smartdoor_debug.log`. If you want to show debug log,
    use `--debug` option.
    """
    log = Path().home() / "smartdoor.log" if not debug else Path().home() / "smartdoor_debug.log"

    if log.exists():
        click.echo(log.read_text())
    else:
        click.echo("log file not found.")


@cli.command()
@click.option("--show", is_flag=True, help="show current configuration parameters")
@click.option(
    "--generate", is_flag=True, help="generate default config file as ~/.config/smartdoor.toml"
)
def config(show: bool, generate: bool):
    """Configuration tool for SmartDoor system.

    If you want to configure smartdoor system, edit `~/.config/smartdoor.toml` directly, after
    generating default config file by `--generate` option.
    """
    # Load default configuration file
    default_config_path = Path(__file__).parent / "default_config.toml"
    with default_config_path.open("rb") as file:
        config = tomllib.load(file)

    # Load user-specific configuration file if exists
    config_path = Path.home() / ".config" / "smartdoor.toml"
    if config_path.exists():
        with config_path.open("rb") as file:
            config.update(tomllib.load(file))

    # If config file not found and `--generate` option is specified, generate default config file
    if generate and not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as file:
            file.write(default_config_path.read_text())
        click.echo(f"generated default config file as {config_path}")

    # Show configuation
    elif show:
        click.echo(pformat(config))
    else:
        click.echo("please specify `--show` or `--generate` option")


@cli.command()
@click.option("--register", is_flag=True, help="register service to systemd and start it")
@click.option("--unregister", is_flag=True, help="unregister service from systemd")
@click.option("--start", is_flag=True, help="start service")
@click.option("--stop", is_flag=True, help="stop service")
def service(register: bool, unregister: bool, start: bool, stop: bool):
    """Systemd Service tool for SmartDoor system.

    If you want to register/unregister smartdoor system to/from systemd, use `--register` or
    `--unregister` option. If choose `--register` option, smartdoor system will be started.
    """
    if register:
        service_file = Path(__file__).parent / "smartdoor.service"
        subprocess.run(
            ["sudo", "ln", "-s", str(service_file), "/etc/systemd/system/smartdoor.service"]
        )
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        subprocess.run(["sudo", "systemctl", "enable", "smartdoor.service"])
        click.echo("registered service to systemd")

    elif unregister:
        subprocess.run(["sudo", "systemctl", "stop", "smartdoor.service"])
        subprocess.run(["sudo", "systemctl", "disable", "smartdoor.service"])
        click.echo("unregistered service from systemd")

    elif start:
        subprocess.run(["sudo", "systemctl", "start", "smartdoor.service"])
        click.echo("started service")

    elif stop:
        subprocess.run(["sudo", "systemctl", "stop", "smartdoor.service"])
        click.echo("stopped service")

    else:
        click.echo("please specify `--register` or `--unregister` option")


if __name__ == "__main__":
    cli()
