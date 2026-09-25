# Raspberry Pi 40-pin status LED

> **Training fixture — NOT FOR MANUFACTURE.** This is a simple external LED breakout
> for workflow practice, not a HAT, electrical release, or purchasing BOM.

The example connects BCM GPIO17 through R1 (1 kΩ) to D1, then back to ground. J1 is
only a two-pin host harness; it does not represent the full Raspberry Pi header or
supply power.

| J1 pin | Host connection                        | Board net     | Purpose   |
| ------ | -------------------------------------- | ------------- | --------- |
| 1      | 40-pin header physical 11 / BCM GPIO17 | GPIO17_STATUS | LED drive |
| 2      | 40-pin header physical 6 / GND         | GND           | Return    |

The Python example is at examples/projects/raspberry-pi-status-led/firmware/status_led.py. It uses
GPIO Zero's BCM numbering and blinks GPIO17.

Raspberry Pi GPIO is a 3.3 V logic domain. Do not connect 5 V to GPIO17, and do not omit the series
resistor. Check the official
[Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
and the exact board's mechanical/electrical documentation before making a real design.
