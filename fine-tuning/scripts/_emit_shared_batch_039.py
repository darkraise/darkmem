"""One-off emitter for shared-base batch-039 — technical domain (hardware / embedded / IoT / firmware).

Writes 50 rows to data/v2/shared/batch_039.tmp.jsonl with ids shared-01901..01950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_039.tmp.jsonl"
ID_OFFSET = 1900

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("ESP32-S3 dual-core firmware pinned the Wi-Fi stack to core 0 and the sensor loop to core 1; the jitter on the I2S buffer disappeared.", "architecture", "technical", False,
     [("ESP32-S3", "technology"), ("Wi-Fi", "protocol"), ("I2S", "protocol")],
     [],
     "how was jitter on the audio DMA buffer eliminated on the dual-core MCU",
     "core pinning wireless sensor loop jitter audio buffer"),
    # --- 2 ---
    ("ESP-IDF replaced Arduino-ESP32 for the telemetry firmware; component manager and FreeRTOS tunables justified the port effort.", "decision", "technical", False,
     [("ESP-IDF", "framework"), ("Arduino-ESP32", "framework"), ("FreeRTOS", "platform")],
     [("ESP-IDF", "Arduino-ESP32", "REPLACES")],
     "which SDK took over from the Arduino core for the telemetry build",
     "IDF replacement component manager kernel tunables port"),
    # --- 3 ---
    ("Raspberry Pi Pico SDK pairs with FreeRTOS on the second core; USB CDC logging stayed on core 0 to avoid tearing prints.", "architecture", "technical", False,
     [("Raspberry Pi Pico SDK", "framework"), ("FreeRTOS", "platform"), ("USB CDC", "protocol")],
     [],
     "how is logging kept clean when an RTOS runs on the second Pico core",
     "Pico second core RTOS serial log tear prevent"),
    # --- 4 ---
    ("Zephyr RTOS device tree overlays carried the custom board pinmux; vendor HAL edits were removed from the firmware tree entirely.", "decision", "technical", False,
     [("Zephyr RTOS", "platform")],
     [],
     "which mechanism pushed board-specific pinmux out of the firmware source",
     "device tree overlay pinmux vendor HAL clean separation"),
    # --- 5 ---
    ("Embassy async Rust on the RP2040 replaced a bespoke cooperative scheduler; async/await reads cleaner than the old state machine.", "decision", "technical", False,
     [("Embassy", "framework"), ("Rust", "language"), ("RP2040", "technology")],
     [("Embassy", "Rust", "USES")],
     "which async framework displaced the hand-rolled scheduler on the RP2040",
     "async embedded cooperative state machine cleaner replace"),
    # --- 6 ---
    ("RTIC framework was preferred over bare-metal interrupts for priority-based scheduling; compile-time resource checks caught two races.", "preference", "technical", False,
     [("RTIC", "framework")],
     [],
     "which Rust embedded framework won on compile-time concurrency safety",
     "priority schedule resource check compile time race catch"),
    # --- 7 ---
    ("nRF52840 won the low-power telemetry design over STM32L0 and EFM32; BLE stack maturity and Zephyr support clinched it.", "decision", "technical", False,
     [("nRF52840", "technology"), ("STM32L0", "technology"), ("EFM32", "technology"), ("BLE", "protocol"), ("Zephyr", "platform")],
     [("nRF52840", "STM32L0", "REPLACES")],
     "which microcontroller was chosen for the battery-powered telemetry node",
     "low power MCU compare wireless stack RTOS support choice"),
    # --- 8 ---
    ("LoRaWAN gateway moved from The Things Network to a self-hosted ChirpStack; Helium was rejected on coverage uncertainty for the farm site.", "decision", "technical", False,
     [("LoRaWAN", "protocol"), ("The Things Network", "service"), ("ChirpStack", "framework"), ("Helium", "service")],
     [("ChirpStack", "The Things Network", "REPLACES")],
     "which LoRaWAN backend displaced TTN for the rural deployment",
     "gateway self host coverage farm site reject network"),
    # --- 9 ---
    ("Matter over Thread replaced the proprietary Zigbee-based lighting bridge; a Thread border router on the Apple TV handled commissioning.", "decision", "technical", False,
     [("Matter", "protocol"), ("Thread", "protocol"), ("Zigbee", "protocol"), ("Apple TV", "technology")],
     [("Matter", "Zigbee", "REPLACES")],
     "which smart-home protocol took over from the vendor Zigbee bridge",
     "border router commissioning smart home bridge swap"),
    # --- 10. noise ---
    ("Hold on, let me reflow that joint.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("BLE GATT profile design put telemetry under one primary service with indicate-only characteristics; notify flooded the central on reconnect.", "problem", "technical", False,
     [("BLE", "protocol"), ("GATT", "protocol")],
     [],
     "why did the BLE profile switch from notify to indicate on telemetry characteristics",
     "profile characteristic indicate notify flood reconnect issue"),
    # --- 12 ---
    ("MQTT topic hierarchy reshuffled to site/device/metric from the flat device-id scheme; wildcard subscriptions on the bridge became trivial.", "architecture", "technical", False,
     [("MQTT", "protocol")],
     [],
     "how was the MQTT namespace reorganised to simplify bridge subscriptions",
     "topic tree wildcard bridge subscription reshape flat"),
    # --- 13 ---
    ("OPC UA replaced raw Modbus TCP on the production line; typed address space and server discovery beat register maps on maintainability.", "decision", "technical", False,
     [("OPC UA", "protocol"), ("Modbus TCP", "protocol")],
     [("OPC UA", "Modbus TCP", "REPLACES")],
     "which industrial protocol took over from register-mapped Modbus",
     "typed address discovery maintainability industrial protocol"),
    # --- 14 ---
    ("OTA update strategy moved to A/B partitions with MCUboot; a failed boot auto-rolls back without a factory-reset trip on-site.", "architecture", "technical", False,
     [("MCUboot", "framework")],
     [],
     "how does the fleet recover from a bricked firmware without a truck roll",
     "partition rollback auto revert boot failure field recovery"),
    # --- 15 ---
    ("U-Boot stayed on the i.MX8 gateway; Coreboot was evaluated but board support for the SoC was not upstream yet.", "decision", "technical", False,
     [("U-Boot", "framework"), ("i.MX8", "technology"), ("Coreboot", "framework")],
     [],
     "which bootloader survived the gateway refresh and why not the alternative",
     "gateway bootloader compare upstream board support absent"),
    # --- 16 ---
    ("JTAG debugging with a PEMicro Multilink unblocked a tricky clock tree bug on the K22F; SWD alone could not reach the trace port.", "problem", "technical", False,
     [("JTAG", "protocol"), ("PEMicro Multilink", "tool"), ("K22F", "technology"), ("SWD", "protocol")],
     [],
     "which debug probe got access to the trace port when SWD did not suffice",
     "probe trace port clock tree bug debug adapter need"),
    # --- 17 ---
    ("OpenOCD with an FT2232H adapter replaced a Segger J-Link on the fab-bench setup; licence counts stopped gating parallel debug sessions.", "decision", "technical", False,
     [("OpenOCD", "tool"), ("FT2232H", "technology"), ("Segger J-Link", "tool")],
     [("OpenOCD", "Segger J-Link", "REPLACES")],
     "which open debug stack displaced the licensed probe on the test bench",
     "open source probe licence gate parallel session bench"),
    # --- 18 ---
    ("Saleae Logic Pro 16 captured the I2C glitch on the power sequencer; rise-time on SDA dropped below spec at 3.3 V.", "problem", "technical", False,
     [("Saleae Logic Pro 16", "tool"), ("I2C", "protocol")],
     [],
     "which analyser caught the bus rise-time glitch on the power sequencer",
     "logic capture bus rise time spec power sequencer"),
    # --- 19 ---
    ("DSLogic Plus took over the everyday captures; the Saleae got shelved for remote sites because DSView ran offline cleanly.", "preference", "technical", False,
     [("DSLogic Plus", "tool"), ("Saleae", "tool"), ("DSView", "tool")],
     [("DSLogic Plus", "Saleae", "REPLACES")],
     "which budget logic analyser replaced the premium one for remote captures",
     "budget analyser remote offline capture prefer shelve"),
    # --- 20 ---
    ("Signal integrity check on the CAN bus used a MSO5074 with a differential probe; ringing on the dominant edge pointed at a missing termination.", "problem", "technical", False,
     [("CAN", "protocol"), ("MSO5074", "tool")],
     [],
     "which scope setup found the CAN termination fault by ringing pattern",
     "differential probe ringing edge termination missing scope"),
    # --- 21 ---
    ("KiCad 8 replaced Altium for the new breakout board; the solder-mask expansion defaults aligned with JLCPCB without tweaks.", "decision", "technical", False,
     [("KiCad 8", "tool"), ("Altium", "tool"), ("JLCPCB", "service")],
     [("KiCad 8", "Altium", "REPLACES")],
     "which PCB CAD took over for the breakout board after the Altium era",
     "CAD swap mask default fab align tweak free"),
    # --- 22 ---
    ("EAGLE was retired after Autodesk's licensing change; legacy schematics convert to KiCad via the plugin cleanly for most boards.", "decision", "technical", False,
     [("EAGLE", "tool"), ("Autodesk", "organization"), ("KiCad", "tool")],
     [("KiCad", "EAGLE", "REPLACES")],
     "which PCB tool got retired in the Autodesk licensing fallout",
     "legacy schematic convert licence change retire tool"),
    # --- 23 ---
    ("JLCPCB handled the five-off prototype run at half the OSH Park quote; panelisation plus shared rails kept the unit cost down.", "decision", "technical", False,
     [("JLCPCB", "service"), ("OSH Park", "service")],
     [],
     "which fab house won the cost comparison for the small prototype batch",
     "fab quote prototype panel shared rail unit cost"),
    # --- 24 ---
    ("OSH Park still wins on the purple four-layer boards; fine-line routing on the RF section came back cleaner than JLC's eco option.", "preference", "technical", False,
     [("OSH Park", "service"), ("JLC", "service")],
     [],
     "which fab keeps the RF board work despite being more expensive",
     "four layer RF fine line routing clean purple prefer"),
    # --- 25 ---
    ("SMD reflow on a PCBite hot plate beat the toaster oven for 0402 passives; thermocouple-logged profiles kept tombstoning at bay.", "preference", "technical", False,
     [("PCBite", "tool")],
     [],
     "which reflow method won on tiny passives in the bench workflow",
     "hot plate oven reflow profile thermocouple tombstone small"),
    # --- 26 ---
    ("A Controleo3-driven oven took over from manual hot-plate reflow once board count passed ten; lead-free profiles needed the ramp control.", "decision", "technical", False,
     [("Controleo3", "tool")],
     [],
     "which controller justified moving back to an oven reflow flow",
     "oven controller ramp profile lead free volume move"),
    # --- 27 ---
    ("Yosys plus nextpnr synthesised the ECP5 design end-to-end; Lattice Diamond was kept only for the IP core wizard step.", "architecture", "technical", False,
     [("Yosys", "tool"), ("nextpnr", "tool"), ("ECP5", "technology"), ("Lattice Diamond", "tool")],
     [],
     "which open FPGA toolchain handles the ECP5 build without the vendor suite",
     "open synthesis place route vendor IP wizard kept"),
    # --- 28 ---
    ("Quartus Prime Lite stayed on the Cyclone IV board; nextpnr's Intel support was not ready for that family on our Quartus version.", "fact", "technical", False,
     [("Quartus Prime Lite", "tool"), ("Cyclone IV", "technology"), ("nextpnr", "tool")],
     [],
     "which FPGA family still requires the vendor tool in the bench flow",
     "Intel family vendor tool open toolchain gap family"),
    # --- 29 ---
    ("Lattice ECP5-EVN dev board drove the first Verilator co-sim harness; waveforms matched the silicon on the SPI loopback test.", "milestone", "technical", False,
     [("Lattice ECP5-EVN", "technology"), ("Verilator", "tool"), ("SPI", "protocol")],
     [],
     "which FPGA board first validated the Verilator harness against real silicon",
     "dev board co simulation waveform match loopback milestone"),
    # --- 30 ---
    ("Verilator 5 cycle-accurate models replaced QuestaSim for the nightly regression; licence freedom let us fan runs across the CI fleet.", "decision", "technical", False,
     [("Verilator 5", "tool"), ("QuestaSim", "tool")],
     [("Verilator 5", "QuestaSim", "REPLACES")],
     "which simulator took over the nightly FPGA regression on CI",
     "cycle accurate licence free CI fan nightly regression"),
    # --- 31 ---
    ("RISC-V vector extension 1.0 landed in the SoC design; the convolution inner loop dropped to a third of the scalar cycle count.", "milestone", "technical", False,
     [("RISC-V", "technology")],
     [],
     "which ISA extension delivered the big convolution speedup on the SoC",
     "vector extension scalar cycle inner loop speedup"),
    # --- 32 ---
    ("Tock OS was considered for the secure-element firmware but Zephyr's broader driver catalogue won the slot; Tock goes on the follow-on project.", "decision", "technical", False,
     [("Tock OS", "platform"), ("Zephyr", "platform")],
     [("Zephyr", "Tock OS", "REPLACES")],
     "which RTOS lost to Zephyr on driver coverage for the secure element",
     "secure element driver catalogue consider RTOS pick future"),
    # --- 33 ---
    ("Nordic's nRF Connect SDK wraps Zephyr with connectivity stacks; the mesh sample was the starting point for the lighting prototype.", "architecture", "technical", False,
     [("nRF Connect SDK", "framework"), ("Zephyr", "platform")],
     [("nRF Connect SDK", "Zephyr", "USES")],
     "which vendor SDK gave the lighting prototype its mesh starting point",
     "vendor wrap connectivity stack mesh sample start"),
    # --- 34. noise ---
    ("Give me a minute to wiggle the probe.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("STM32CubeIDE was dropped for the G4 motor board; PlatformIO with CMake fit the existing Bazel monorepo better than the Eclipse fork.", "decision", "technical", False,
     [("STM32CubeIDE", "tool"), ("PlatformIO", "tool"), ("CMake", "tool"), ("Bazel", "tool")],
     [("PlatformIO", "STM32CubeIDE", "REPLACES")],
     "which IDE got displaced for the motor board to fit the monorepo",
     "IDE drop monorepo build integrate Eclipse fork fit"),
    # --- 36 ---
    ("PX4 Autopilot firmware flashed onto the Pixhawk 6X for the survey drone; the uORB message bus suited the custom payload driver.", "architecture", "technical", False,
     [("PX4 Autopilot", "framework"), ("Pixhawk 6X", "technology"), ("uORB", "protocol")],
     [],
     "which autopilot stack and bus carried the custom survey drone payload",
     "autopilot message bus payload driver survey drone"),
    # --- 37 ---
    ("Yocto Project built the Variscite i.MX8 image; Buildroot was faster to bring up but Yocto's layer model won on SBOM compliance.", "decision", "technical", False,
     [("Yocto Project", "framework"), ("Variscite i.MX8", "technology"), ("Buildroot", "framework")],
     [("Yocto Project", "Buildroot", "REPLACES")],
     "which Linux image builder met the SBOM requirement for the gateway",
     "layer model compliance software bill materials builder"),
    # --- 38 ---
    ("Buildroot still produces the tiny recovery initramfs; a 14 MB image boots the field-service shell inside eight seconds.", "fact", "technical", False,
     [("Buildroot", "framework")],
     [],
     "which builder stayed on for the compact recovery image",
     "tiny initramfs recovery shell boot time compact"),
    # --- 39 ---
    ("CAN-FD replaced classical CAN on the trailer harness; the 2 Mb/s data phase cleared the periodic diagnostic window without overrun.", "decision", "technical", False,
     [("CAN-FD", "protocol"), ("CAN", "protocol")],
     [("CAN-FD", "CAN", "REPLACES")],
     "which in-vehicle bus replaced classical CAN to clear the diagnostic window",
     "flexible data rate bus trailer diagnostic overrun clear"),
    # --- 40 ---
    ("TSN on the factory ethernet ring delivered bounded latency for the motion controller; PTP grandmaster ran on the managed switch.", "architecture", "technical", False,
     [("TSN", "protocol"), ("PTP", "protocol")],
     [],
     "which ethernet feature set gave the motion controller bounded latency",
     "time sensitive bound latency master switch ring factory"),
    # --- 41 ---
    ("Zigbee Pro was retired from the 2026 product line; Matter over Thread handles the same mesh with native smart-home onboarding.", "decision", "technical", False,
     [("Zigbee Pro", "protocol"), ("Matter", "protocol"), ("Thread", "protocol")],
     [("Matter", "Zigbee Pro", "REPLACES")],
     "which mesh protocol took over from Zigbee Pro in the current product line",
     "mesh retire product line onboarding native smart home"),
    # --- 42 ---
    ("LittleFS replaced SPIFFS on the ESP32 product; power-fail safety and smaller code footprint carried the decision.", "decision", "technical", False,
     [("LittleFS", "framework"), ("SPIFFS", "framework"), ("ESP32", "technology")],
     [("LittleFS", "SPIFFS", "REPLACES")],
     "which embedded filesystem displaced the older ESP flash filesystem",
     "flash filesystem power fail safe footprint swap embedded"),
    # --- 43 ---
    ("TinyUSB drove the composite CDC-plus-HID device on the RP2040 board; the vendor-supplied stack kept timing out on Windows 11 hosts.", "decision", "technical", False,
     [("TinyUSB", "library"), ("CDC", "protocol"), ("HID", "protocol"), ("RP2040", "technology"), ("Windows 11", "platform")],
     [],
     "which USB stack replaced the flaky vendor driver for the composite device",
     "composite serial input device host timeout stack swap"),
    # --- 44 ---
    ("Segger emWin was dropped for LVGL on the HMI display; flash footprint fell 40 percent and the theming API suited our designers.", "decision", "technical", False,
     [("Segger emWin", "library"), ("LVGL", "library")],
     [("LVGL", "Segger emWin", "REPLACES")],
     "which GUI library took over the HMI after the commercial stack",
     "GUI swap flash footprint theme API designer preference"),
    # --- 45 ---
    ("Protothreads powered the legacy AVR firmware; the MSP430 port keeps them for drop-in parity until the Rust rewrite lands.", "fact", "technical", False,
     [("Protothreads", "library"), ("AVR", "technology"), ("MSP430", "technology"), ("Rust", "language")],
     [],
     "which legacy concurrency library stays in the MSP430 tree for now",
     "legacy cooperative port parity drop rewrite pending"),
    # --- 46 ---
    ("Nordic Thingy:91 prototyped the cellular IoT node on LTE-M; nRF Cloud logs fed the provisioning dashboard during field trials.", "architecture", "technical", False,
     [("Nordic Thingy:91", "technology"), ("LTE-M", "protocol"), ("nRF Cloud", "service")],
     [],
     "which dev kit and cloud drove the cellular field trial provisioning",
     "cellular prototype narrowband cloud log provisioning trial"),
    # --- 47 ---
    ("Particle Boron was rejected in favour of the Nordic plus Quectel BG95 combo; BOM cost and long-term cellular module availability decided it.", "decision", "technical", False,
     [("Particle Boron", "technology"), ("Nordic", "organization"), ("Quectel BG95", "technology")],
     [],
     "which integrated cellular module lost to a discrete MCU-plus-modem combo",
     "integrated module BOM availability discrete modem combo"),
    # --- 48 ---
    ("SEGGER SystemView traced the FreeRTOS task churn; priority inversion between the SPI ISR and the sensor task surfaced in minutes.", "problem", "technical", False,
     [("SEGGER SystemView", "tool"), ("FreeRTOS", "platform"), ("SPI", "protocol")],
     [],
     "which tracer exposed the priority inversion inside the FreeRTOS build",
     "system trace task priority inversion interrupt inspect"),
    # --- 49 ---
    ("Percepio Tracealyzer was evaluated against SystemView; SystemView won on RP2040 support and lower runtime overhead for our build.", "decision", "technical", False,
     [("Percepio Tracealyzer", "tool"), ("SystemView", "tool"), ("RP2040", "technology")],
     [("SystemView", "Percepio Tracealyzer", "REPLACES")],
     "which tracer lost the bake-off on overhead and chip support",
     "compare tracer overhead chip support evaluation outcome"),
    # --- 50 ---
    ("Renode simulated the nRF52 plus BME280 board in CI on 2026-02-18; hardware-in-the-loop queues drained after the switch.", "milestone", "technical", False,
     [("Renode", "tool"), ("nRF52", "technology"), ("BME280", "technology"), ("2026-02-18", "date")],
     [],
     "when did the board simulation land and unblock the hardware-in-the-loop queue",
     "simulator CI virtual board HIL queue drain date"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
