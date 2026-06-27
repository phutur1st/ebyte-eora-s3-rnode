# Pin map & board identity

Ebyte EoRa-S3 (E22-900MM22S module, ESP32-S3 + Semtech SX1262), as sold by
Rabbit-Labs as the **RL-ReadyNode**. Pin map confirmed against both the
Meshtastic `CDEBYTE_EoRa-S3` variant and the MeshCore `ebyte_eora-s3` board.

## Radio (SX1262, SPI)

| Signal      | GPIO |
|-------------|------|
| NSS / CS    | 7    |
| SCK         | 5    |
| MOSI        | 6    |
| MISO        | 3    |
| BUSY        | 34   |
| DIO1 / IRQ  | 33   |
| RESET       | 8    |
| TXEN / RXEN | —    (handled internally via DIO2 RF switch) |

- `DIO2_AS_RF_SWITCH` = **true**
- `HAS_TCXO` = **false** — this unit uses a **crystal (XTAL)**, not a TCXO.
  Meshtastic documents the EoRa-S3-900TB as XTAL. Enabling TCXO makes the radio
  report online but never transmit or receive. (MeshCore sets a 1.8 V TCXO,
  which appears to be a different hardware revision — do not copy it for this
  board.)

## Peripherals

| Function        | GPIO | Notes |
|-----------------|------|-------|
| OLED I2C SDA    | 18   | 0.96" SSD1306 @ 0x3C |
| OLED I2C SCL    | 17   | |
| OLED reset      | —    | not wired (DISP_RST -1) |
| Status LED      | 37   | single LED used for RX+TX |
| Button          | 0    | BOOT/strapping pin; only RESET is exposed externally |
| Battery ADC     | 1    | LiPo via 2×1 MΩ divider (see [features.md](features.md)) |

## Identity codes

| Constant              | Value | Meaning |
|-----------------------|-------|---------|
| `PRODUCT_EBYTE_EORA`  | 0xEC  | product family |
| `BOARD_EBYTE_EORA_S3` | 0x46  | board model |
| `MODEL_D8`            | 0xD8  | 868/915 MHz SX1262 variant |

> These IDs are self-allocated for this port. If upstreaming to RNode CE / RNS,
> coordinate them to avoid collisions with future official assignments.
