"""Probe the Desay VW-update library: strings, hash-constant signatures, referenced paths.

libsvapi_vw.so.1.4.0 (27,282 B) exports svapi_vw_upgrade_package_is_valid / read_pkg_md5_info /
rollback_get/set / upgrade_copy_to_emmc, and imports ONLY librt, libdrm, libdrm_omap, libc.
If a cryptographic signature were used, we would expect OpenSSL/libcrypto imports or RSA
constants. Internal MD5/SHA implementations have recognisable init-constant patterns.
"""
import os, re, struct, sys

LIB = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin\rootfs\usr\lib\libsvapi_vw.so.1.4.0'
BASE = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin\rootfs\usr\lib\libsvapi.so.1.3.0'

# well-known hash init constants (little-endian byte order as they appear in .rodata)
CONSTS = {
    'MD5-init-block (67452301 efcdab89 98badcfe 10325476)':
        bytes.fromhex('0123456789abcdeffedcba9876543210'),
    'SHA1-init-block (67452301 EFCDAB89 98BADCFE 10325476 C3D2E1F0)':
        bytes.fromhex('0123456789abcdeffedcba9876543210f0e1d2c3'),
    'SHA256-init-block':
        bytes.fromhex('67e6096a85ae67bb72f36e3c3af54fa57f520e518c68059babd9831f19cde05b'),
    'MD5 K[0..3] (d76aa478 e8c7b756 242070db c1bdceee)':
        bytes.fromhex('78a46ad756b7c7e8db702024eecebdc1'),
    'MD5 K[4..7] (f57c0faf 4787c62a a8304613 fd469501)':
        bytes.fromhex('af0f7cf52ac68747134630a8019546fd'),
    'AES / empty-key pattern': bytes(16),
}

for path in (LIB, BASE):
    print('=' * 78)
    print(os.path.basename(path), f'({os.path.getsize(path):,} bytes)')
    print('=' * 78)
    data = open(path, 'rb').read()
    found = False
    for label, sig in CONSTS.items():
        if len(sig) >= 8:
            n = data.count(sig)
            if n:
                print(f'  HASH CONSTANT PRESENT: {label}  (occurrences={n})')
                found = True
    if not found:
        print('  no MD5/SHA init or round constants found in this file')

    strs = sorted({m.group().decode('latin1') for m in re.finditer(rb'[\x20-\x7e]{4,}', data)})
    print(f'\n  ASCII strings ({len(strs)}):')
    for s in strs:
        print('    ' + s[:180])
