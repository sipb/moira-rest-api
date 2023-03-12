"""
Python code to convert the credential format from the WebAthena JSON response
into a credential cache ("ccache") that actual desktop utilities or APIs can use

make_ccache is the important function (the rest are helper functions)

Taken from SSH (shellinabox) example in https://github.com/davidben/webathena.
"""

import base64
import struct
from tempfile import NamedTemporaryFile

# Some DER encoding stuff. Bleh. This is because the ccache contains a
# DER-encoded krb5 Ticket structure, whereas Webathena deserializes
# into the various fields. Re-encoding in the client would be easy as
# there is already an ASN.1 implementation, but in the interest of
# limiting MIT Kerberos's exposure to malformed ccaches, encode it
# ourselves. To that end, here's the laziest DER encoder ever.
def _der_encode_length(l: int) -> bytes:
    if l <= 127:
        return bytes([l])
    out: bytes = b""
    while l > 0:
        out = bytes([l & 0xff]) + out
        l >>= 8
    out = bytes([len(out) | 0x80]) + out
    return out

def _der_encode_tlv(tag: int, value) -> bytes:
    return bytes([tag]) + _der_encode_length(len(value)) + value

def _der_encode_integer_value(val: int) -> bytes:
    # base 256, MSB first, two's complement, minimum number of octets
    # necessary. This has a number of annoying edge cases:
    # * 0 and -1 are 0x00 and 0xFF, not the empty string.
    # * 255 is 0x00 0xFF, not 0xFF
    # * -256 is 0xFF 0x00, not 0x00

    # Special-case to avoid an empty encoding.
    if val == 0:
        return b"\x00"
    sign = 0 # What you would get if you sign-extended the current high bit.
    out: bytes = b""
    # We can stop once sign-extension matches the remaining value.
    while val != sign:
        byte = val & 0xff
        out = bytes([byte]) + out
        sign = -1 if byte & 0x80 == 0x80 else 0
        val >>= 8
    return out

def _der_encode_integer(val: int) -> bytes:
    return _der_encode_tlv(0x02, _der_encode_integer_value(val))
def _der_encode_int32(val: int) -> bytes:
    if val < -2147483648 or val > 2147483647:
        raise ValueError("Bad value")
    return _der_encode_integer(val)
def _der_encode_uint32(val: int) -> bytes:
    if val < 0 or val > 4294967295:
        raise ValueError("Bad value")
    return _der_encode_integer(val)

def _der_encode_string(val: str) -> bytes:
    return _der_encode_tlv(0x1b, val.encode("utf-8"))

def _der_encode_octet_bytes(val: bytes) -> bytes:
    return _der_encode_tlv(0x04, val)

def _der_encode_sequence(tlvs: list[bytes | None], tagged: bool=True) -> bytes:
    body: list[bytes] = []
    for i, tlv in enumerate(tlvs):
        # Missing optional elements represented as None.
        if not tlv:
            continue
        if tagged:
            # Assume kerberos-style explicit tagging of components.
            tlv = _der_encode_tlv(0xa0 | i, tlv)
        body.append(tlv)
    return _der_encode_tlv(0x30, b"".join(body))

def _der_encode_ticket(tkt: dict) -> bytes:
    return _der_encode_tlv(
        0x61, # Ticket
        _der_encode_sequence(
            [_der_encode_integer(5), # tktVno
             _der_encode_string(tkt["realm"]),
             _der_encode_sequence( # PrincipalName
                    [_der_encode_int32(tkt["sname"]["nameType"]),
                     _der_encode_sequence([_der_encode_string(c)
                                          for c in tkt["sname"]["nameString"]],
                                         tagged=False)]),
             _der_encode_sequence( # EncryptedData
                    [_der_encode_int32(tkt["encPart"]["etype"]),
                     (_der_encode_uint32(tkt["encPart"]["kvno"])
                      if "kvno" in tkt["encPart"]
                      else None),
                     _der_encode_octet_bytes(
                                base64.b64decode(tkt["encPart"]["cipher"]))])]))

# Kerberos ccache writing code. Using format documentation from here:
# http://www.gnu.org/software/shishi/manual/html_node/The-Credential-Cache-Binary-File-Format.html

def _ccache_counted_octet_bytes(data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + data

def _ccache_principal(name: dict, realm: str) -> bytes:
    header: bytes = struct.pack("!II", name["nameType"], len(name["nameString"]))
    return (header + _ccache_counted_octet_bytes(realm.encode('utf-8')) +
            b"".join(_ccache_counted_octet_bytes(c.encode("utf-8"))
                    for c in name["nameString"]))

def _ccache_key(key: dict) -> bytes:
    return (struct.pack("!H", key["keytype"]) +
            _ccache_counted_octet_bytes(base64.b64decode(key["keyvalue"])))

def _flags_to_uint32(flags: list) -> int:
    ret = 0
    for i, v in enumerate(flags):
        if v:
            ret |= 1 << (31 - i)
    return ret

def _ccache_credential(cred: dict) -> bytes:
    out: bytes = _ccache_principal(cred["cname"], cred["crealm"])
    out += _ccache_principal(cred["sname"], cred["srealm"])
    out += _ccache_key(cred["key"])
    out += struct.pack("!IIII",
                       cred["authtime"] // 1000,
                       cred.get("starttime", cred["authtime"]) // 1000,
                       cred["endtime"] // 1000,
                       cred.get("renewTill", 0) // 1000)
    out += struct.pack("!B", 0)
    out += struct.pack("!I", _flags_to_uint32(cred["flags"]))
    # TODO: Care about addrs or authdata? Former is "caddr" key.
    out += struct.pack("!II", 0, 0)
    out += _ccache_counted_octet_bytes(_der_encode_ticket(cred["ticket"]))
    # No second_ticket.
    out += _ccache_counted_octet_bytes(b"")
    return out

def make_ccache(cred: dict) -> bytes:
    # Do we need a DeltaTime header? The ccache I get just puts zero
    # in there, so do the same.
    out: bytes = struct.pack("!HHHHII",
                      0x0504, # file_format_version
                      12, # headerlen
                      1, # tag (DeltaTime)
                      8, # taglen (two uint32_ts)
                      0, 0, # time_offset / usec_offset
                      )
    out += _ccache_principal(cred["cname"], cred["crealm"])
    out += _ccache_credential(cred)
    return out


# Manual testing
if __name__ == '__main__':
    import subprocess
    import os
    import json
    import moira

    with open('private-test-ticket.json', 'rb') as f:
        cred = json.loads(f.read().decode())

    with NamedTemporaryFile(prefix='ccache_') as ccache:
        ccache.write(make_ccache(cred))
        ccache.flush()
        env = dict(os.environ)
        env['KRB5CCNAME'] = ccache.name

        # Make sure ticket works
        username = cred['cname']['nameString'][0]
        subprocess.call(['klist'], env=env)

        # Make sure Moira works
        moira.connect()
        moira.auth('python3')
        print(moira.query('get_user_by_login', username)[0])