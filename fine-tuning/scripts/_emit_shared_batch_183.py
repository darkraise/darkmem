"""One-off emitter for shared-base batch-183 — technical domain (embedded and RTOS systems: FreeRTOS, Zephyr, NuttX, RTIC, embassy, ESP-IDF, Cortex-M, RP2040, nRF52840, DMA, ISR, mutex, watchdog, CAN, I2C, SPI, low-power).

Writes 50 rows to data/v2/shared/batch_183.tmp.jsonl with ids shared-09101..09150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_183.tmp.jsonl"
ID_OFFSET = 9100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Swapped the bare-metal super-loop for FreeRTOS on the STM32F4 sensor node; two independent deadlines finally stopped starving each other when the radio ISR went long.", "decision", "technical", False,
     [("FreeRTOS", "framework"), ("STM32F4", "platform"), ("super-loop", "pattern"), ("radio ISR", "pattern")],
     [("FreeRTOS", "super-loop", "REPLACES")],
     "which RTOS displaced the super-loop on the STM32F4 sensor node and what scheduling pain did it cure",
     "freertos super loop stm32f4 sensor deadline radio isr starve"),
    # --- 2 --- architecture
    ("Zephyr drives the nRF52840 beacon firmware; the device-tree overlay pins GPIO, I2C, and SPI assignments so board revs swap hardware without touching application code.", "architecture", "technical", False,
     [("Zephyr", "framework"), ("nRF52840", "platform"), ("device-tree overlay", "pattern"), ("I2C", "protocol"), ("SPI", "protocol")],
     [("Zephyr", "nRF52840", "DEPLOYED_ON"), ("device-tree overlay", "I2C", "CONFIGURES")],
     "how does the nRF52840 beacon firmware isolate board revisions from application code",
     "zephyr nrf52840 device tree overlay gpio i2c spi board rev"),
    # --- 3 --- milestone
    ("Shipped the embassy async port on RP2040 in firmware v1.4; the old RTIC build worked but async/await let the radio and flash-writer share a core cleanly.", "milestone", "technical", False,
     [("embassy", "framework"), ("RP2040", "platform"), ("RTIC", "framework"), ("v1.4", "date")],
     [("embassy", "RTIC", "REPLACES")],
     "which async Rust framework replaced RTIC on the RP2040 and in which firmware release",
     "embassy rtic rp2040 firmware 1 4 async await radio flash port"),
    # --- 4 --- problem
    ("Priority inversion on the SD-card logger stalled the control loop for twelve milliseconds; switched the FreeRTOS mutex from plain to priority-inheriting and the latency spike vanished.", "problem", "technical", False,
     [("Priority inversion", "concept"), ("SD-card logger", "service"), ("FreeRTOS", "framework"), ("priority-inheriting", "pattern")],
     [("priority-inheriting", "Priority inversion", "FIXES")],
     "which mutex flavour fixed the twelve millisecond control-loop stall caused by the SD-card logger",
     "priority inversion freertos mutex inheritance sd card logger stall"),
    # --- 5 --- architecture
    ("DMA ping-pong buffers feed the I2S microphone on ESP32-S3; the CPU only wakes on half-full and full interrupts, which dropped audio-capture overhead to about two percent.", "architecture", "technical", False,
     [("DMA", "concept"), ("I2S", "protocol"), ("ESP32-S3", "platform"), ("ping-pong buffers", "pattern")],
     [("ping-pong buffers", "DMA", "USES")],
     "how does the ESP32-S3 audio capture path minimise CPU overhead when streaming from the I2S microphone",
     "dma ping pong buffer i2s microphone esp32 s3 half full interrupt"),
    # --- 6 --- decision
    ("Picked RTIC over embassy for the motor-controller firmware because static priority scheduling gave tighter worst-case ISR latency bounds than an async executor could guarantee.", "decision", "technical", False,
     [("RTIC", "framework"), ("embassy", "framework"), ("motor-controller", "project"), ("ISR latency", "concept")],
     [("RTIC", "embassy", "PREFERS")],
     "why did the motor-controller firmware choose RTIC over embassy and which timing metric decided it",
     "rtic embassy motor controller isr latency static priority schedule"),
    # --- 7 --- fact
    ("The coin-cell power budget on the CR2032 asset tag is 220 microamps average; the nRF52840 runs at 3.3 volts and the system-off sleep draws about 1.9 microamps with RAM retention.", "fact", "technical", False,
     [("CR2032", "infrastructure"), ("nRF52840", "platform"), ("system-off", "pattern")],
     [],
     "what average current budget and sleep-mode draw shape the CR2032 asset-tag design on nRF52840",
     "cr2032 coin cell nrf52840 system off sleep microamp budget retention"),
    # --- 8 --- decision
    ("Ring buffer between the UART ISR and the parser task is lock-free SPSC with power-of-two size; a single read of the write index gives the ISR enough consistency without disabling interrupts.", "decision", "technical", False,
     [("Ring buffer", "pattern"), ("UART", "protocol"), ("SPSC", "pattern"), ("ISR", "concept")],
     [("Ring buffer", "UART", "APPLIES_TO")],
     "which ring-buffer discipline lets the UART ISR publish bytes to the parser without masking interrupts",
     "ring buffer uart isr spsc lock free power of two write index"),
    # --- 9 --- fact
    ("Watchdog resets during OTA on the ESP32-C3 traced to the flash-erase stretching past the timeout; split the erase into chunks and fed the task-watchdog between chunks to stop the resets.", "fact", "technical", False,
     [("Watchdog", "concept"), ("OTA", "concept"), ("ESP32-C3", "platform"), ("task-watchdog", "api")],
     [("task-watchdog", "Watchdog", "FIXES")],
     "what caused the OTA-time watchdog resets on ESP32-C3 and how did chunking the erase save it",
     "watchdog ota esp32 c3 flash erase chunk task feed timeout reset"),
    # --- 10. noise ---
    ("The lab's soldering iron has a yellow sticky note that reads do not touch, the tip and the iron itself disagree on which one it means.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- decision
    ("TockOS got picked for the secure-enclave product because its userland capsule model keeps third-party drivers from touching the kernel address space; CMSIS-RTOS2 came close but lacked the isolation story.", "decision", "technical", False,
     [("TockOS", "framework"), ("CMSIS-RTOS2", "framework"), ("secure-enclave", "project"), ("capsule", "pattern")],
     [("TockOS", "CMSIS-RTOS2", "PREFERS")],
     "which RTOS won the secure-enclave bake-off and which isolation feature was the deciding factor",
     "tockos cmsis rtos2 secure enclave capsule isolation kernel address"),
    # --- 12 --- decision
    ("CAN bus frames on the vehicle gateway flow through a two-stage pipeline: a hard-real-time ISR fills a ring, then a lower-priority task parses DBC decoded signals into the telemetry blob.", "decision", "technical", False,
     [("CAN bus", "protocol"), ("DBC", "technology"), ("telemetry", "service"), ("vehicle gateway", "project")],
     [("CAN bus", "telemetry", "COMMUNICATES_WITH")],
     "how does the vehicle gateway decouple CAN frame reception from DBC decoding into telemetry",
     "can bus dbc telemetry vehicle gateway isr ring parse two stage"),
    # --- 13 --- reference
    ("The ARM Cortex-M7 Technical Reference Manual documents cache maintenance for DMA coherency; DCache clean-and-invalidate around buffers is the pattern the HAL cribs from directly.", "reference", "technical", False,
     [("ARM Cortex-M7", "platform"), ("DMA coherency", "concept"), ("HAL", "library")],
     [("HAL", "DMA coherency", "IMPLEMENTS")],
     "which ARM Cortex-M7 manual section drives the HAL's DMA cache-maintenance pattern for coherency",
     "cortex m7 reference manual dma coherency dcache clean invalidate hal"),
    # --- 14 --- milestone
    ("First silicon of the RISC-V MCU booted Zephyr to shell on 2026-02-11; interrupt controller emulation disagreed with the hardware on three vector numbers and the patch shipped same week.", "milestone", "technical", False,
     [("RISC-V MCU", "platform"), ("Zephyr", "framework"), ("2026-02-11", "date"), ("interrupt controller", "concept")],
     [("Zephyr", "RISC-V MCU", "DEPLOYED_ON")],
     "when did the RISC-V MCU first boot Zephyr to a shell and what emulator disagreement slowed it",
     "riscv mcu zephyr boot shell interrupt controller vector february"),
    # --- 15 --- preference
    ("Prefer PlatformIO over raw STM32Cube generation for new boards; the library dependency pinning is saner and CI can reproduce the exact firmware binary that shipped last quarter.", "preference", "technical", False,
     [("PlatformIO", "tool"), ("STM32Cube", "tool"), ("CI", "infrastructure")],
     [("PlatformIO", "STM32Cube", "PREFERS")],
     "which build tool does the team pick over STM32Cube and which reproducibility win drives the choice",
     "platformio stm32cube build tool dependency pin reproducible ci"),
    # --- 16 --- decision
    ("ESP-IDF component manager pulls the radio stack and lwIP as versioned components; the main app's idf_component.yml pins exact hashes so firmware archaeology on a shipped rev still compiles.", "decision", "technical", False,
     [("ESP-IDF", "framework"), ("lwIP", "library"), ("idf_component.yml", "file")],
     [("ESP-IDF", "lwIP", "DEPENDS_ON")],
     "how does the ESP-IDF component manager keep shipped firmware revisions reproducible years later",
     "esp idf component manager lwip idf yml hash pin reproducible"),
    # --- 17 --- problem
    ("ISR latency regressed to 14 microseconds on the nRF Connect SDK upgrade; the new softdevice claimed more of the NVIC priority band, and moving the motor-control IRQ below it restored the 2 microsecond figure.", "problem", "technical", False,
     [("nRF Connect SDK", "framework"), ("softdevice", "library"), ("NVIC", "concept"), ("motor-control", "project")],
     [("softdevice", "NVIC", "CONFIGURES")],
     "which NVIC priority shuffle fixed the 14 microsecond ISR latency regression after the nRF Connect SDK bump",
     "nrf connect sdk softdevice nvic priority motor control isr latency"),
    # --- 18 --- decision
    ("Chose deep-sleep with RTC wakeup over light-sleep on the ESP32-C3 sensor; the 5 microamp quiescent current hit the two-year AA budget and light-sleep's 800 microamps blew it by an order of magnitude.", "decision", "technical", False,
     [("deep-sleep", "pattern"), ("light-sleep", "pattern"), ("RTC", "concept"), ("ESP32-C3", "platform")],
     [("deep-sleep", "light-sleep", "REPLACES")],
     "which ESP32-C3 sleep mode hit the two-year AA current budget and by how much did it beat light-sleep",
     "esp32 c3 deep sleep light sleep rtc wake aa battery microamp"),
    # --- 19 --- reference
    ("CMSIS-DSP gives biquad filters, FFTs, and matrix ops tuned for Cortex-M4 and Cortex-M7 with DSP extensions; the audio team's EQ pipeline leans on arm_biquad_cascade_df1_f32 directly.", "reference", "technical", False,
     [("CMSIS-DSP", "library"), ("Cortex-M4", "platform"), ("Cortex-M7", "platform"), ("arm_biquad_cascade_df1_f32", "api")],
     [("CMSIS-DSP", "arm_biquad_cascade_df1_f32", "HAS_PART")],
     "which CMSIS-DSP primitive powers the EQ pipeline on Cortex-M4 and M7 audio products",
     "cmsis dsp biquad cortex m4 m7 eq audio arm cascade df1"),
    # --- 20 --- milestone
    ("NuttX on the flight controller runs POSIX threads for the sensor fusion task and a dedicated work-queue for the MAVLink telemetry; the file-descriptor abstraction lets /dev/ttyS3 swap for a USB-CDC path in sim.", "milestone", "technical", False,
     [("NuttX", "framework"), ("POSIX", "api"), ("MAVLink", "protocol"), ("USB-CDC", "protocol"), ("flight controller", "project")],
     [("NuttX", "POSIX", "IMPLEMENTS")],
     "how does NuttX on the flight controller separate sensor fusion from MAVLink while supporting sim swap",
     "nuttx posix thread mavlink work queue usb cdc ttys3 swap flight"),
    # --- 21 --- decision
    ("Dropped bare-metal in favour of Zephyr on the Teensy-class board; the driver ecosystem for the external SPI flash and ADC was already upstream and saved two weeks of glue code.", "decision", "technical", False,
     [("bare-metal", "pattern"), ("Zephyr", "framework"), ("Teensy", "platform"), ("SPI flash", "infrastructure")],
     [("Zephyr", "bare-metal", "REPLACES")],
     "why did the Teensy-class board swap bare-metal for Zephyr and which upstream drivers justified it",
     "teensy zephyr bare metal spi flash adc driver upstream glue code"),
    # --- 22 --- fact
    ("The RP2040 has two Cortex-M0+ cores and a programmable IO block; core1 runs the PIO-driven WS2812 stream so core0 can keep USB-CDC latency under a millisecond.", "fact", "technical", False,
     [("RP2040", "platform"), ("Cortex-M0+", "platform"), ("PIO", "concept"), ("WS2812", "infrastructure"), ("USB-CDC", "protocol")],
     [("PIO", "WS2812", "PRODUCES")],
     "how does the RP2040 firmware split work between its two Cortex-M0+ cores and the PIO block",
     "rp2040 cortex m0 plus pio ws2812 usb cdc latency core split"),
    # --- 23 --- fact
    ("The I2C bus locked up after a power glitch on the sensor harness; a clock-recovery sequence that toggles SCL nine times before a STOP frees the slave and the driver now runs it on bus-error.", "fact", "technical", False,
     [("I2C", "protocol"), ("SCL", "concept"), ("clock-recovery", "method"), ("sensor harness", "infrastructure")],
     [("clock-recovery", "I2C", "FIXES")],
     "which recovery sequence frees an I2C bus that a slave has wedged low after a power glitch",
     "i2c bus lock clock recovery scl stop nine toggle sensor slave"),
    # --- 24 --- architecture
    ("Firmware logging on low-power builds writes to a circular flash region with erase-ahead; a separate brown-out detector forces a flush of the RAM ring to flash before voltage drops past 2.4 volts.", "architecture", "technical", False,
     [("brown-out detector", "infrastructure"), ("circular flash", "pattern"), ("RAM ring", "pattern")],
     [("brown-out detector", "RAM ring", "CAUSES")],
     "how does the firmware preserve recent log entries across a brown-out without a dedicated supercap",
     "brown out detector flash ring ram flush 2 4 volt erase ahead"),
    # --- 25 --- milestone
    ("Passed the CAN bus conformance test on the vehicle gateway during the 2026-03-04 validation run; the loopback mode and a CANoe capture matched the DBC decoder bit-for-bit across 50000 frames.", "milestone", "technical", False,
     [("CAN bus", "protocol"), ("vehicle gateway", "project"), ("2026-03-04", "date"), ("CANoe", "tool"), ("DBC", "technology")],
     [("CANoe", "CAN bus", "APPLIES_TO")],
     "which vehicle-gateway conformance milestone landed on 2026-03-04 and how was the frame stream validated",
     "can bus conformance vehicle gateway canoe dbc loopback validation"),
    # --- 26 --- reference
    ("ARM's Procedure Call Standard AAPCS pins the stack alignment ISRs must restore; violating the 8-byte alignment corrupts VFP context save on Cortex-M4F and the symptom looks like random FPU register mangling.", "reference", "technical", False,
     [("AAPCS", "publication"), ("Cortex-M4F", "platform"), ("VFP", "concept")],
     [("AAPCS", "VFP", "APPLIES_TO")],
     "which ARM calling-convention rule governs ISR stack alignment and how does breaking it mangle VFP state",
     "aapcs cortex m4f vfp stack alignment isr 8 byte fpu register"),
    # --- 27 --- preference
    ("Prefer mutex over semaphore for shared state; the priority-inheritance contract makes worst-case reasoning tractable while a counting semaphore hides the owner and lets inversions creep back in.", "preference", "technical", False,
     [("mutex", "concept"), ("semaphore", "concept"), ("priority-inheritance", "pattern")],
     [("mutex", "semaphore", "PREFERS")],
     "which synchronisation primitive does the team prefer for shared state and which property drives the preference",
     "mutex semaphore priority inheritance worst case shared state"),
    # --- 28 --- architecture
    ("Bootloader partition layout on the nRF52840 reserves 48 KB for MCUboot, dual 384 KB slots for primary and secondary, and a scratch region; image signing uses ed25519 checked on every cold boot.", "architecture", "technical", False,
     [("nRF52840", "platform"), ("MCUboot", "tool"), ("ed25519", "algorithm")],
     [("MCUboot", "ed25519", "USES")],
     "how is the nRF52840 flash carved up for MCUboot and which signature algorithm gates cold boot",
     "nrf52840 mcuboot partition ed25519 image sign cold boot slot"),
    # --- 29 --- fact
    ("SPI clock glitching on the flash chip showed up as random sector-read errors; the culprit was a missing series resistor on the FPC harness, and adding a 33 ohm resistor cleaned the edges.", "fact", "technical", False,
     [("SPI", "protocol"), ("FPC harness", "infrastructure"), ("33 ohm resistor", "infrastructure")],
     [("33 ohm resistor", "SPI", "FIXES")],
     "which hardware tweak cured the SPI flash read errors traced to clock-edge glitching on the FPC harness",
     "spi flash clock glitch fpc harness 33 ohm series resistor edge"),
    # --- 30 --- decision
    ("Adopted CMSIS-RTOS2 as the RTOS API on mixed Cortex-M vendors; a single call set lets the same application run on NXP, ST, and Nordic silicon without rewriting the task and queue wiring.", "decision", "technical", False,
     [("CMSIS-RTOS2", "framework"), ("Cortex-M", "platform"), ("NXP", "organization"), ("Nordic", "organization")],
     [("CMSIS-RTOS2", "Cortex-M", "APPLIES_TO")],
     "which RTOS API lets the same firmware run across NXP, ST, and Nordic Cortex-M silicon unchanged",
     "cmsis rtos2 cortex m nxp nordic st portable application task"),
    # --- 31 --- architecture
    ("Zephyr's work-queue pattern runs the BLE GAP callbacks off the ISR; the radio softdevice pushes events to a system work-queue so the application only sees thread-context notifications.", "architecture", "technical", False,
     [("Zephyr", "framework"), ("BLE GAP", "protocol"), ("work-queue", "pattern"), ("softdevice", "library")],
     [("softdevice", "work-queue", "USES")],
     "how does Zephyr keep BLE GAP callbacks out of ISR context on softdevice-based radios",
     "zephyr ble gap work queue softdevice isr thread context radio"),
    # --- 32 --- fact
    ("Typical ISR latency on a Cortex-M4 with FreeRTOS at 84 MHz sits near 300 nanoseconds for the hardware entry plus 1.2 microseconds for the kernel portion before the handler body runs.", "fact", "technical", False,
     [("Cortex-M4", "platform"), ("FreeRTOS", "framework"), ("ISR latency", "concept")],
     [],
     "what ISR latency numbers does the team expect from a 84 MHz Cortex-M4 running FreeRTOS",
     "cortex m4 freertos isr latency 84 mhz 300 nanosecond kernel enter"),
    # --- 33 --- decision
    ("Picked embassy's time driver over cortex-m-rt's default for the async firmware; the tickless design lets the MCU stay in wait-for-event between timer deadlines and slashed average power.", "decision", "technical", False,
     [("embassy", "framework"), ("cortex-m-rt", "library"), ("tickless", "pattern"), ("wait-for-event", "pattern")],
     [("embassy", "cortex-m-rt", "PREFERS")],
     "which timer driver did the async firmware pick and what low-power behaviour did tickless unlock",
     "embassy cortex m rt time driver tickless wait for event power"),
    # --- 34 --- problem
    ("Stack overflow on the FreeRTOS idle hook crashed the device whenever TLS handshakes ran; bumped the task stack from 2 KB to 6 KB after the run-time stack high-water mark exposed the growth.", "problem", "technical", False,
     [("FreeRTOS", "framework"), ("idle hook", "pattern"), ("TLS", "protocol"), ("high-water mark", "method")],
     [("high-water mark", "FreeRTOS", "APPLIES_TO")],
     "which diagnostic exposed the TLS-triggered FreeRTOS idle-hook stack overflow and what fix shipped",
     "freertos idle hook tls stack overflow high water mark 2k 6k"),
    # --- 35 --- architecture
    ("Real-time constraints on the servo loop demand a 1 kHz jitter ceiling of 50 microseconds; a TIM timer IRQ at highest NVIC priority drives the control step and FreeRTOS tasks run below it.", "architecture", "technical", False,
     [("servo loop", "project"), ("TIM timer", "infrastructure"), ("NVIC", "concept"), ("FreeRTOS", "framework")],
     [("TIM timer", "servo loop", "CONFIGURES")],
     "how does the servo-loop firmware guarantee a 1 kHz control step under 50 microseconds of jitter",
     "servo loop 1khz jitter 50us tim nvic priority freertos task"),
    # --- 36 --- reference
    ("The FreeRTOS-Plus-TCP documentation spells out the zero-copy receive path; app code grabs an IP packet buffer from the stack and releases it after parsing rather than memcpy-ing into a local.", "reference", "technical", False,
     [("FreeRTOS-Plus-TCP", "library"), ("zero-copy", "pattern"), ("IP", "protocol")],
     [("FreeRTOS-Plus-TCP", "zero-copy", "IMPLEMENTS")],
     "which network-stack pattern does FreeRTOS-Plus-TCP document for avoiding receive-path memcpy",
     "freertos plus tcp zero copy receive ip buffer release parse"),
    # --- 37 --- milestone
    ("Hit the 2-year shelf-life target on the asset-tag battery acceptance test; the 48-hour accelerated soak on 2026-01-22 projected 760 days against a 600 day spec after duty-cycle fit.", "milestone", "technical", False,
     [("asset-tag", "project"), ("2026-01-22", "date"), ("accelerated soak", "method")],
     [("accelerated soak", "asset-tag", "APPLIES_TO")],
     "which asset-tag battery milestone did the 2026-01-22 soak test validate and by how much did it beat spec",
     "asset tag 2 year battery soak 48 hour 760 day 600 spec duty"),
    # --- 38 --- architecture
    ("Shared buffers between the application CPU and the Cortex-M0 sensor coprocessor live in a non-cacheable MPU region; cache-maintenance calls around DMA descriptors aren't needed on this boundary.", "architecture", "technical", False,
     [("Cortex-M0", "platform"), ("MPU", "concept"), ("non-cacheable", "pattern"), ("DMA", "concept")],
     [("MPU", "non-cacheable", "CONFIGURES")],
     "how do the application CPU and Cortex-M0 coprocessor share buffers without per-transfer cache flushes",
     "mpu non cacheable cortex m0 coprocessor dma shared buffer region"),
    # --- 39 --- preference
    ("Prefer static allocation of FreeRTOS tasks and queues over xTaskCreate with heap_4; boot-time footprint becomes predictable and the linker map tells you the exact RAM budget up front.", "preference", "technical", False,
     [("static allocation", "pattern"), ("FreeRTOS", "framework"), ("xTaskCreate", "api"), ("heap_4", "library")],
     [("static allocation", "heap_4", "PREFERS")],
     "which FreeRTOS allocation discipline does the team prefer and why does it simplify RAM budgeting",
     "freertos static allocation xtaskcreate heap 4 linker map ram"),
    # --- 40 --- decision
    ("Picked a software watchdog layered on top of the hardware IWDG; each critical task checks in to the software watchdog which then kicks IWDG, so a stuck task starves the kick and forces reset.", "decision", "technical", False,
     [("software watchdog", "pattern"), ("IWDG", "infrastructure")],
     [("software watchdog", "IWDG", "USES")],
     "how does the layered watchdog catch stuck tasks while still riding on IWDG's hardware backstop",
     "software watchdog iwdg hardware kick stuck task check in reset"),
    # --- 41 --- architecture
    ("The fuel-gauge driver reads SOC over I2C every 30 seconds and broadcasts a battery event on the Zephyr message bus; any subscriber can throttle work without polling the chip itself.", "architecture", "technical", False,
     [("fuel-gauge", "infrastructure"), ("I2C", "protocol"), ("Zephyr", "framework"), ("message bus", "pattern")],
     [("fuel-gauge", "message bus", "COMMUNICATES_WITH")],
     "how do Zephyr subscribers react to battery state-of-charge without each polling the fuel-gauge over I2C",
     "fuel gauge i2c zephyr message bus soc subscribe throttle event"),
    # --- 42 --- milestone
    ("The STM32H7 D-cache aliased DMA writes from the Ethernet MAC; clean-and-invalidate around descriptor rings plus the MPU marking them non-cacheable stopped the intermittent ping drops.", "milestone", "technical", False,
     [("STM32H7", "platform"), ("D-cache", "concept"), ("Ethernet MAC", "infrastructure"), ("MPU", "concept")],
     [("MPU", "D-cache", "FIXES")],
     "which cache-coherency fix stopped the intermittent Ethernet ping drops on STM32H7 descriptor rings",
     "stm32h7 d cache ethernet mac mpu non cacheable ping drop dma"),
    # --- 43. noise ---
    ("The office coffee machine has developed a two-tone gurgle that the intern insists predicts Mondays with better accuracy than the calendar.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- decision
    ("Chose UART at 921600 baud over SPI for the debug trace port; the single-wire TX line freed up a pin for the production test connector and the throughput still clears the trace volume.", "decision", "technical", False,
     [("UART", "protocol"), ("SPI", "protocol"), ("debug trace", "pattern"), ("production test", "pattern")],
     [("UART", "SPI", "PREFERS")],
     "which trace-port bus won the pin-budget trade versus SPI and why did UART at 921600 baud fit",
     "uart spi debug trace 921600 baud pin budget production test"),
    # --- 45 --- architecture
    ("Bare-metal vs RTOS trade-off on the battery-powered sensor landed on RTOS; the deterministic tick let the radio, sensor, and watchdog obligations compose without a hand-rolled scheduler growing scary.", "architecture", "technical", False,
     [("Bare-metal", "pattern"), ("RTOS", "concept"), ("battery-powered sensor", "project"), ("scheduler", "concept")],
     [("RTOS", "Bare-metal", "REPLACES")],
     "why did the battery-powered sensor pick an RTOS over bare-metal and which obligations drove composition",
     "bare metal rtos battery sensor scheduler radio watchdog compose"),
    # --- 46 --- fact
    ("Flash wear-levelling on the LittleFS partition assumes 100000 erase cycles per sector; the logger writes about 40 sectors per day, which projects roughly seven years before a block retires.", "fact", "technical", False,
     [("LittleFS", "library"), ("Flash wear-levelling", "concept"), ("logger", "service")],
     [],
     "what erase-cycle budget does LittleFS assume and how does the logger's daily write volume project lifetime",
     "littlefs flash wear leveling 100000 erase sector logger daily"),
    # --- 47 --- reference
    ("The Zephyr Device Driver Model document defines the API for syscall-safe drivers; the i2c_write_read call the sensor pipe uses comes straight from section 3 of that reference.", "reference", "technical", False,
     [("Zephyr", "framework"), ("Device Driver Model", "publication"), ("i2c_write_read", "api")],
     [("i2c_write_read", "Device Driver Model", "IMPLEMENTS")],
     "which Zephyr reference document defines the syscall-safe driver API that the sensor pipe leans on",
     "zephyr device driver model i2c write read syscall safe section 3"),
    # --- 48 --- reference
    ("ARM Cortex-M33 adds TrustZone-M; the Secure and Non-secure banked stack pointers let the secure partition host the crypto library while the non-secure app drives the UI.", "reference", "technical", False,
     [("Cortex-M33", "platform"), ("TrustZone-M", "concept"), ("crypto library", "library")],
     [("Cortex-M33", "TrustZone-M", "HAS_PART")],
     "which Cortex-M33 security feature hosts the crypto library separately from the non-secure UI app",
     "cortex m33 trustzone m secure non banked stack crypto ui"),
    # --- 49 --- preference
    ("Prefer cooperative yield points in the main control task over forced preemption; reasoning about shared state stays local and the worst-case response still hits the 2 millisecond budget.", "preference", "technical", False,
     [("cooperative yield", "pattern"), ("preemption", "concept"), ("control task", "project")],
     [("cooperative yield", "preemption", "PREFERS")],
     "which scheduling discipline does the main control task prefer and which response-time budget still holds",
     "cooperative yield preempt control task shared state 2 ms budget"),
    # --- 50 --- milestone
    ("The Cortex-M7 port of the audio pipeline hit DSP parity with the reference build on 2026-03-28; the CMSIS-DSP biquad cascade clocked 1.4 microseconds per frame against a 5 microsecond budget.", "milestone", "technical", False,
     [("Cortex-M7", "platform"), ("audio pipeline", "project"), ("2026-03-28", "date"), ("CMSIS-DSP", "library")],
     [("CMSIS-DSP", "audio pipeline", "APPLIES_TO")],
     "which Cortex-M7 audio-pipeline milestone landed on 2026-03-28 and how did CMSIS-DSP hit the frame budget",
     "cortex m7 audio pipeline cmsis dsp biquad 1 4 us 5 budget march"),
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
