# Arduino Uno R3 status LED

> **Training fixture — NOT FOR MANUFACTURE.** This is a simple external LED breakout
> for workflow practice, not an Arduino shield, electrical release, or purchasing BOM.

The example connects Arduino Uno R3 D13 / LED_BUILTIN through R1 (1 kΩ) to D1, then
back to ground. J1 is only a two-pin host harness; it does not represent the full Uno
header or provide board power.

| J1 pin | Host connection          | Board net  | Purpose   |
| ------ | ------------------------ | ---------- | --------- |
| 1      | Uno R3 D13 / LED_BUILTIN | D13_STATUS | LED drive |
| 2      | Uno R3 GND               | GND        | Return    |

The sketch is at examples/projects/arduino-uno-status-led/firmware/arduino-uno-status-led.ino. It
uses LED_BUILTIN, so the same sketch blinks the Uno's onboard indicator and this external training
LED when the harness is fitted.

Use the official [Arduino Uno R3 documentation](https://docs.arduino.cc/hardware/uno-rev3)
and [pinout](https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf) when
checking a real board revision. Select a real LED, resistor power rating, header,
mechanical arrangement, and approved part identities before any production use.
