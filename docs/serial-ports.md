# Serial ports, per operating system

`flipperkit devices` lists every serial port it can see and marks the ones that look
like a Flipper Zero. When it marks nothing, or marks the wrong thing, the cause is
almost always the operating system rather than FlipperKit — the port has to exist and
be openable by your user before any of this code runs.

This page records what the Flipper actually enumerates as, what each OS does with
that, and which of it `flipperkit` can rely on. It is the background for
[#1](https://github.com/juandresrodca/FlipperKit/issues/1) (make `--port` optional).

## What the device presents

The Flipper Zero is an STM32WB55 and exposes its CLI as a **USB CDC-ACM virtual
serial port**. Over USB it identifies itself as:

| Descriptor | Value |
|---|---|
| `idVendor` | `0x0483` (STMicroelectronics) |
| `idProduct` | `0x5740` (STM32 Virtual COM Port) |
| `iManufacturer` | `Flipper Devices Inc.` |
| `iProduct` | `Virtual Port` |
| `iSerialNumber` | `flip_<DeviceName>` — your Flipper's name, as set in *Settings → Desktop* |

Two things follow from that table, and they pull in opposite directions.

**`0483:5740` is not unique to the Flipper.** It is the identity pair in ST's stock
CDC example, so it is shared with bare STM32 Nucleo and Blue Pill boards, several
3D-printer control boards and a long tail of hobby hardware that never changed the
template. Matching on VID/PID alone finds a Flipper, but it also finds those.

**`iSerialNumber` is the discriminating field.** Nothing else on a normal machine sets
a serial number beginning `flip_`, and it is the one descriptor that carries the
device's own name. pyserial exposes it as `port.serial_number`.

`client.is_flipper_port()` matches VID/PID first and falls back to the description and
manufacturer strings. It does **not** look at `serial_number` yet — see
[Where the current detection is weak](#where-the-current-detection-is-weak).

## Windows

Port name: **`COM3`**, `COM4`, … — the number is assigned per device serial number and
persists across replugs, so a given Flipper keeps the same COM port on a given machine.

```powershell
flipperkit devices
flipperkit info --port COM3
```

No driver install is needed. Windows 10 and 11 bind CDC-ACM devices to the in-box
`usbser.sys` automatically, and the device appears under **Ports (COM & LPT)** in
Device Manager as *STMicroelectronics Virtual COM Port*. If it instead appears under
**Other devices** with a warning triangle, the CDC interface did not bind — replug into
a different port and check the cable is a data cable rather than a charge-only one,
which is the single most common cause of a Flipper that charges but never enumerates.

Only one process may hold a COM port. If `flipperkit` reports *Could not open COM3*,
close qFlipper, the Flipper Web/Lab browser tab and any serial terminal first; the port
is exclusive and the loser gets *Access is denied*.

Port numbers above `COM9` need the `\\.\` prefix in some tools. pyserial handles this
itself, so `--port COM14` works as written.

## macOS

Port name: **`/dev/cu.usbmodemflip_<DeviceName>1`**. macOS builds the node name from
`iSerialNumber`, which is why the device's own name appears in the path.

```bash
ls /dev/cu.usbmodem*
flipperkit devices
flipperkit info --port /dev/cu.usbmodemflip_Mercury1
```

**Use `cu.*`, not `tty.*`.** Both nodes appear for the same device. The `tty.*` node is
the *call-in* device: opening it blocks until DCD is asserted, which a CDC-ACM gadget
never does, so the open hangs rather than failing. The `cu.*` node is the *call-out*
device and opens immediately. `available_ports()` lists whatever pyserial enumerates —
if you see both, pick the `cu.` one.

No driver and no permission setup: the in-box `AppleUSBACM` driver claims the device
and the node is world-writable.

## Linux

Port name: **`/dev/ttyACM0`**, `ttyACM1`, … assigned by the `cdc_acm` module in plug
order, so it is *not* stable across replugs or reboots.

```bash
flipperkit devices
flipperkit info --port /dev/ttyACM0
```

### Permissions

Out of the box the node is `root:dialout` mode `0660`, so a non-root user gets
*Permission denied*. Add yourself to the owning group rather than running the tool as
root:

```bash
stat -c '%G' /dev/ttyACM0     # dialout on Debian/Ubuntu, uucp on Arch/Fedora
sudo usermod -aG dialout "$USER"
```

Group membership is read at login, so log out and back in — `newgrp dialout` fixes the
current shell only.

### ModemManager

On a desktop distribution, ModemManager probes any new `ttyACM` device to see whether
it is a cellular modem. It holds the port for several seconds and sends AT commands at
it while it does. The symptom is a `flipperkit` command that fails immediately after
plugging in but succeeds if you wait, or a Flipper CLI that returns truncated
responses. Tell ModemManager to leave the device alone in the same udev rule that fixes
the naming:

```
# /etc/udev/rules.d/42-flipper.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", \
  MODE="0660", GROUP="dialout", SYMLINK+="flipper", ENV{ID_MM_DEVICE_IGNORE}="1"
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
flipperkit info --port /dev/flipper
```

`SYMLINK+="flipper"` gives a stable path that survives replugs. With more than one
Flipper, key the symlink on the serial number instead —
`ATTRS{serial}=="flip_Mercury", SYMLINK+="flipper-mercury"` — since the numbered
`ttyACM*` nodes can swap between them.

## Where the current detection is weak

`flipperkit devices` already marks candidate ports, and the logic lives in
[`is_flipper_port()`](../src/flipperkit/client.py). Three gaps are worth stating plainly
before #1 turns the marking into an automatic choice:

1. **`serial_number` is unused.** It is the only descriptor that is specific to a
   Flipper, and pyserial reports it on all three platforms. A
   `serial_number.startswith("flip")` check should rank above the description match.
2. **The `stmicroelectronics` description hint is broad.** It is what makes a Nucleo
   board or an STM32-based printer register as a candidate. It is a reasonable *last*
   resort, but it should not outrank a serial-number match.
3. **Ambiguity has no defined behaviour.** `devices` prints a warning when it finds
   more than one candidate and leaves the choice to the operator. Auto-detection needs
   a rule instead: exactly one candidate proceeds, zero or several is an error naming
   what was found, and `--port` always wins. Silently picking the first port on a bench
   with two Flippers on it is the one outcome worse than asking.

Confirm the descriptors on your own device before relying on point 1 — the table at the
top is what the Flipper firmware sets, but a custom firmware may not:

```bash
python -c "from serial.tools import list_ports; [print(p.device, p.vid, p.pid, p.serial_number, p.description) for p in list_ports.comports()]"
```

On Linux, `lsusb -v -d 0483:5740 | grep iSerial` shows the same field without pyserial.

## Nothing shows up at all

In roughly the order worth trying:

1. **The cable.** Charge-only USB-C cables are common and the Flipper charges happily
   over one while never enumerating. Swap it for a known data cable first.
2. **The device is in another mode.** A Flipper in DFU/recovery presents a *DFU in FS
   mode* device on `0483:df11`, not a serial port. Reboot it from the menu.
3. **Another process owns the port.** qFlipper, the Flipper Web browser tab and any
   open serial terminal all hold it exclusively. Close them.
4. **pyserial is missing.** `flipperkit devices` says so explicitly —
   `pip install pyserial`, or reinstall the package, which depends on it.
5. **A virtual machine did not forward the device.** USB passthrough has to be enabled
   per device; WSL2 needs `usbipd` and does not pass USB through by default.

Everything except the first two is visible in `flipperkit devices` output, so run that
before reaching for `dmesg`.
