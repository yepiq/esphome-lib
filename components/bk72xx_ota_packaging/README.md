# Beken OTA packaging

The shared Beken base loads this build-only component. Its PlatformIO post script ensures
PyCryptodome is installed in LibreTiny's own Python environment before ltchiptool packages
firmware. A known AES-256-CBC vector checks that encryption and decryption preserve the
length of aligned input. Dependency installation or backend failures stop the build.

The declaration in `packages/boards/templates/base-board-libretiny-beken.yaml` enables the
hook for every Beken consumer. Code generation copies `bk72xx_ota_packaging.py` into the
build directory and adds `post:bk72xx_ota_packaging.py` to PlatformIO's `extra_scripts`.
The script runs after LibreTiny configures its Python environment and before firmware
packaging. It declares `pycryptodome>=3.18,<4` through LibreTiny's dependency installer,
keeping the upper bound compatible with ltchiptool 4.15.0's desktop dependency requirement.
Installation is needed only when that dependency is missing or outside the supported range.
The successful check prints `Beken OTA packaging: raw AES-CBC verified` with package versions.
The ELF depends on the script, so adding or changing the hook relinks an existing incremental
build and makes ltchiptool regenerate its cached intermediate RBL images before writing UF2.

ltchiptool 4.15.0 manually pads Beken OTA data, then its PyAES backend adds another padding
block. ARM Linux hosts select PyAES through ltchiptool's dependency markers. The wrapper
was introduced in 3.0.1, and 3.0.2 extended the architecture selection to aarch64.
[Original change](https://github.com/libretiny-eu/ltchiptool/commit/4e97e51283757e4837b86f4614baec85b795041b)
[aarch64 selection](https://github.com/libretiny-eu/ltchiptool/commit/d1fe04a75c5f6e5f98046b7b0ab2aeda1891d964)

The BK7231N 1.0.1 reference bootloader reads compressed input in 4096-byte chunks. When
the extra padding occupies a new chunk after the end of gzip, the loader can finish
decompression before including its remaining partial output in the application hash.
It rejects the image and runs the previous firmware. The occurrence depends on compressed
image length. A successful OTA transfer alone does not establish installation.

This workaround uses LibreTiny 1.13.0's `InstallPythonDependencies` and `LTPYTHONEXE`
build hooks. It is reapplied when the build environment is recreated, including after an
add-on replacement, build-environment reset or Python migration. The dependency lives in
LibreTiny's Python environment on the build host. It remains installed until that environment
is cleaned or the package is explicitly removed, even if the hook is later disabled.

For rollout, refresh the library checkout used by the dashboard and rebuild the firmware.
Check for the successful AES message above before uploading the newly generated image.
After reboot, confirm the device reports the new compilation timestamp. Previously generated
firmware artifacts need regeneration before uploading.

Monitor the upstream AES wrapper and remove this component, its base-board declaration
and this note when the supported ltchiptool release consistently uses raw CBC for every
backend. Verify both PyAES and PyCryptodome against the same aligned input and check a
Beken OTA package from an ARM build host before removing it.
[Upstream wrapper](https://github.com/libretiny-eu/ltchiptool/blob/master/ltchiptool/util/crypto.py)
