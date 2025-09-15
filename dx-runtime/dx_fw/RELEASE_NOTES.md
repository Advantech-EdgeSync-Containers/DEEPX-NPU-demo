# RELEASE_NOTES
## v2.1.0 / 2025-06-25
### 1. Changed
- Update LPDDR Driver
  - Update Training Logic for LPDDR5/LPDDR5x
- Update DCDC IC reset value
  - Enable forced PWM mode
### 2. Fixed
### 3. Added
- Add LPDDR4 Driver
  - Add Support for LPDDR4 (dx_m1m)
- Merge SLT(System Level Test) features
- Add DVS(Dynamic Voltage Scaling) feature to mitigate NPU voltage drop


## v2.0.5 / 2025-05-15
### 1. Changed
- modify event enum value (match with dx-rt and driver)
### 2. Fixed
- None
### 3. Added
- None

## v2.0.4 / 2025-05-12
### 1. Changed
- Update refresh controls and Training repeats
  - Update Refresh Cycle for rm 10 & 11 ( -> x0.25 )
  - Update Training Repeats for 0x8 -> 0x10
- Update pvt 2-point calibration policy
  - Set default value if room (30'C) or hot(90'C) OTP Trim info is not valid 
- Enhance inference logic and change pcie device id(0x01->0x00)
- Always notify throttling works to host

### 2. Fixed
- Implement interrupt handler priority(5)
  - The taskENTER_CRITICAL API only disables interrupts with interrupt priorities higher than 5. There is a possibility of problems when using RTOS APIs on interrupts with interrupt priorities lower than 5. So we adjust the priorities for all interrupts.

### 3. Added
- Add chip offset in device info
  -  chip offset info (0~3) is added for H1, when [identify, get status] from dx-rt

## v2.0.3 / 2025-04-18
### 1. Changed
- None
### 2. Fixed
- Modify NPU error handling logic to notify to host when NPU error occurs.
- Fix DDR channel mode.
### 3. Added
- None

## v2.0.2 / 2025-04-14
### 1. Changed
- None
### 2. Fixed
- Initialize controller settings in case, PCIe linkup succeed on ROM.
- Enforce hot-reset logic.
### 3. Added
- None

## v2.0.1 / 2025-04-09
### 1. Changed
- Update npu core clock manage logic
  - Update NPU core clock manage logic (-> using npu clock skipper)
- Change PCIe Link-up Logic
  - Enforce pcie link up logic with secureloader
  - Change pcie link up logic based on policy and steps
  - Add FEATURE_PCIE_RTOS to seperate compile of rtos and secureloader
  - Merge new feature like register and api tables, debug and log related to pcie Init poilcy then interrupt
  - Reset phy when ctrl init fail and change ctrl reset condition
  - Add perst enable in freertos
  - Enable statemachine task after ltssm is enabled
- Tighten NPU throttling conditions
  - NPU throttling works when ddr temperature status >= 0x9 (85'C)
- NPU Interrupts
  - Change timeout of npu hang(1s -> 3s)
  - Refactoring npu done interrupt logic
### 2. Fixed
- None
### 3. Added
- ADD PVT Temperature Calibration with OTP
  - PVT Temperature Calibration is updated when OTP PVT calibration info exists

## v2.0.0 / 2025-03-24
### 1. Changed
- None
### 2. Fixed
- Fix CPU reset logic
  - Added logic to disable D-cache and perform ISB (Instruction Synchronization Barrier) before CPU reset to address occasional reset failures.
- Fix throttling logic in user region (under 90'C)
  - update frequency when throttling table (for user region) updated by user (dxrt-cli -C)
- fix bounding error
  - fix bounding error when multi-processes are running with multi-bounding options
### 3. Added
- Implement PCIe Register and API Function for PCIe debug interface
- Add boot stage(secure loader)
  - The boot process now proceeds as follows: ROM → Secure Loader → Boot Loader → FreeRTOS.

## v1.6.3 / 2025-02-19
### 1. Changed
- Set LPDDR Frequency by User
    - Add features for setting LPDDR frequency by using $dxrt-cli-internal -t <target_freq>
    - Only Support [5200, 5400, 5600, 5800, 6000, 6200, 6400] Mbps for now
    - [Test]
        - Change LPDDR freq by using dxrt-cli-internal (with -t option)
    - [Related Issue]
        - None
### 2. Fixed
- Fixed Software Hang Issue
    - Fixed an issue where a software hang occurred when the device mode switched to power save mode during inference.
    - Modified the logic to transition to power save mode only if the bounding delete option is provided and no requests are received for 3 seconds.
    - [Test]
        - Performed inference using multiple processes.
        - Conducted inference on the entire ModelZoo.
    - [Related Issue]
        - Regression Fail
### 3. Added
- None


## v1.6.2 / 2025-02-12
### 1. Changed
- Print module revision version by gpio
- Update NPU Throttling driver
    - Emergency Stop (over 100'C): NPU inference will be paused until cool down (95'C)
    - NPU Throttling by Firmware (over 90'C): NPU frequency is managed by firmware
    - NPU Throttling by User (under 90'C): NPU frequency is mangaged by user (dxrt-cli -C)
- Implement QoS Driver
    - Improved the driver to measure DDR bandwidth for each NPU inference.
- Add Device Mode
    - Added device mode classification for power optimization.
    - Idle Mode: Mode where inference is in progress (NPU Clock On).
    - Power Save Mode: Standby state without inference (NPU Clock Off).
### 2. Fixed
- NPU on/off logic
    - Fixed an issue causing the M1 stopped when power off NPU
### 3. Added
- Support LPDDR5/5x by single firmware binary(fw.bin)
    - M.2 : default frequency (5: 5600mhz / 5x: 6400mhz)
    - H1  : default frequency (5: 6000mhz / 5x: 6400mhz)
- Support Single-run M1 chip
    - Disable updates for firmware versions below v1.6.1 (only Single-run chip)
- Add Auto Recovery Function
    - Added an automatic recovery mode when a device error is reported due to internal issues
    - (NPU hang + abnormal software behavior).

## v1.6.1 / 2025-01-10
### 1. Changed
- Remove duplicated images in fw.bin
### 2. Fixed
- Enhance PCIe Link-Up Logic
    - Modified the checking logic to use PhyStatus.
### 3. Added
- 

## v1.6.0 / 2024-12-20
### 1. Changed
- update throttling logic (default off, added cooldown)
### 2. Fixed
- 
### 3. Added
- update throttling config by json file

## v1.5.9 / 2024-12-06
### 1. Changed
- Alert warning to host when NPU temperature reaches emergency threshold
- Alert Error to host when lpddr Link-ECC double-bit error occurs
### 2. Fixed
- Modify the state of inf_flow_mon to disabled
### 3. Added
- SMBUS slave mode for H1 board
- 
## v1.5.8 / 2024-11-22
### 1. Changed
- update pcie link-up logic (timeout 1s -> 5s)
- update throttling logic (default off, mode=step)
### 2. Fixed
- 
### 3. Added
- 

## v1.5.7 / 2024-11-15
### 1. Changed
- Alert NPU error -> NPU event [error, notify] to host
### 2. Fixed
- 
### 3. Added
- NPU recovery concept
- Notify message about thermal throttling & emergency

## v1.5.6 / 2024-11-05
### 1. Changed
-
### 2. Fixed
- disable lpddr temperature interrupt
### 3. Added
- NPU Clock off by message 

## v1.5.4 / 2024-10-29
### 1. Changed
- reduce boot time
- LPDDR Enable duty train
### 2. Fixed
### 3. Added
- Support H1 (quattro) Board with 6.4GHz

## v1.5.3 / 2024-10-28
### 1. Changed
### 2. Fixed
- fix LPDDR low performance problem
### 3. Added

## v1.5.2 / 2024-10-28
### 1. Changed
- Improved function to pass status information to host when an error occurs
- update inference flow monitoring with process id
- pvt 2-point calibration
- ubbpdate pcie revision to support new memory map(0x00->0x01)
### 2. Fixed
- 
### 3. Added
- Idle Hook for Sleep Mode

## v1.5.1 / 2024-10-04
### 1. Changed
- Update lock mechanism for queue
### 2. Fixed
- 
### 3. Added
-

## v1.5.0 / 2024-09-20
### 1. Changed
- LPDDR5 Clock 5.5 GHz
- PCIE link-up logic
### 2. Fixed
- request Q. dequeue bug
### 3. Added
- Nor Flash Booting

## v1.4.7 / 2024-08-05
### 1. Changed
- remove app 'testcase'
### 2. Fixed
- 
### 3. Added
- 

## v1.4.6 / 2024-07-31
### 1. Changed
- fw: pcie link-up check logic
### 2. Fixed
- fw: timer overflow
### 3. Added
- 

## v1.4.5 / 2024-07-23
### 1. Changed
- pcie link-up check logic
### 2. Fixed
- get_timer API overflow
- UART RX Pull-Up for interrupt W/A
### 3. Added
- nor flash driver (by build option)
