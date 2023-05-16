"""Smartdoor system including NFC card detecting, key locking/unlocking, turning LED on/off, etc. 
with Raspberry Pi.
"""

from .smartdoor import SmartDoor


__version__ = "2.0.0.dev"
__all__ = ["SmartDoor"]
