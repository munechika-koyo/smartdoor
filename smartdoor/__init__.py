"""Smartdoor system including NFC card detecting, key locking/unlocking, turning LED on/off, etc.

This system is designed to be used with Raspberry Pi.

Some CLIs including main sequence is implemented here.
"""
from logging import config as log_config
from logging import getLogger
from pathlib import Path
from pprint import pformat

import rich_click as click

# Set logger
log_config.fileConfig(Path(__file__).parent / "logging.conf")
logger = getLogger("main")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .smartdoor import SmartDoor

__version__ = "2.0.0.dev0"
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

    The initial key status can be set by `--locked` or `--unlocked` option, by default `--locked`.

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
    finally:
        door.close()


@cli.command()
@click.option("--debug", "-d", is_flag=True, help="show debug log")
def show_log(debug: bool):
    """Show log file if it exists at `~/smartdoor.log` or `~/smartdoor_debug.log`."""
    log = Path().home() / "smartdoor.log" if not debug else Path().home() / "smartdoor_debug.log"

    if log.exists():
        click.echo(log.read_text())
    else:
        click.echo("log file not found.")


@cli.command()
def show_config():
    """Show configuation in key-value format.

    If user-specific config exists at `~/.config/smartdoor.toml`, overrided one is shown.
    """
    # Load default configuration file
    with open(Path(__file__).parent / "default_config.toml", "rb") as file:
        config = tomllib.load(file)

    # Load user-specific configuration file if exists
    config_path = Path.home() / ".config" / "smartdoor.toml"
    if config_path.exists():
        with open(config_path, "rb") as file:
            config.update(tomllib.load(file))

    # Show configuation
    click.echo(pformat(config))


if __name__ == "__main__":
    cli()
