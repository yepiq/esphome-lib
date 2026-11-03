# Licensing And Third-Party Notices

## Library Scope

Original esphome-lib code and documentation are offered under the [MIT License](LICENSE), except
for the file identified below. This includes commercial reuse. The grant applies to rights held
by the copyright holder, where copyright applies; it does not claim ownership of third-party work
or guarantee that every AI-assisted fragment is independently copyrightable.

Third-party notices and licenses take precedence for their respective material. External
components, ESPHome, platform SDKs, fonts and other build dependencies retain their own licenses.
A firmware binary containing them is not automatically MIT-only: check the licenses of the actual
dependencies when distributing it. This file records identified upstream material, not a warranty
that every dependency or historical contribution has received a complete provenance audit.

## Vevor Weather Decoder

[`devices/vevor-7-in-1.yaml`](devices/vevor-7-in-1.yaml) incorporates a decoder derived from
[`rtl_433/src/devices/vevor_7in1.c`](https://github.com/merbanan/rtl_433/blob/master/src/devices/vevor_7in1.c).
The upstream attribution is:

> Copyright (C) 2024 Bruno OCTAU (ProfBoc75)

The derived device file is distributed under **GPL-2.0-or-later**, not the repository's default
MIT license. It adapts the decoder to ESPHome's SX127x callback and adds ESPHome entities, radio
configuration and reception diagnostics. The upstream file is available under GPL version 2 or,
at your option, any later version. The [GPL version 2 text](LICENSES/GPL-2.0-or-later.txt) is included
unchanged from rtl_433's COPYING file. Retain this attribution and the applicable license when
redistributing the derived source; distribution of firmware also needs the applicable GPL obligations
considered for the combined work.

## Tuya Data Models

Files under [`data-models/tuya`](data-models/tuya/README.md) archive vendor cloud schemas and settings
extracted from original firmware. They are reference data, not newly authored esphome-lib software.
The MIT grant does not relicense third-party rights in those materials. Their presence does not
establish vendor endorsement, hardware safety or a serial protocol implementation.
