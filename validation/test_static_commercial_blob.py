import hashlib
import os
import random
import struct
import sys
import types
import zlib
from pathlib import Path

import pefile
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import nuitka_decompiler as n


def _sample(salt='nuitka'):
    payload = (b'.bytecode\0' + struct.pack('<I', 1) + b'x' +
               b'mod\0' + struct.pack('<I', 2) + b'xy' +
               b'zz\0' + struct.pack('<I', 2) + b'ab')
    plain = struct.pack('<II', zlib.crc32(payload), len(payload)) + payload
    digest = hashlib.md5(plain).digest()
    mapping = list(range(256))
    random.Random(salt).shuffle(mapping)
    last = 0
    encrypted = bytearray(plain[:8])
    for i, c in enumerate(digest + payload):
        encrypted.append(mapping[c] ^ ((last + i) & 255))
        last = (c + digest[i % 8]) & 255
    return payload, plain, bytes(encrypted)


def test_static_commercial_and_corruption(monkeypatch):
    _, plain, encrypted = _sample()
    monkeypatch.setattr(pefile, 'PE', lambda **kw: object())
    assert n._decrypt_blob_if_encrypted('unused', encrypted, pe_data=b'PE') == plain
    corrupt = bytearray(encrypted)
    corrupt[-1] ^= 1
    monkeypatch.setattr(n.CommercialBypass, '_find_all_mapping_candidates', lambda *a, **kw: [])
    monkeypatch.setattr(n.CommercialBypass, 'extract_key_material_from_pe', lambda *a: (None, None))
    assert n._decrypt_blob_if_encrypted('unused', bytes(corrupt), pe_data=b'PE') is None


def test_custom_salt_mapping(monkeypatch):
    _, plain, encrypted = _sample('custom')
    forward = list(range(256))
    random.Random('custom').shuffle(forward)
    inverse = [0] * 256
    for original, encoded in enumerate(forward):
        inverse[encoded] = original
    monkeypatch.setattr(pefile, 'PE', lambda **kw: object())
    monkeypatch.setattr(n.CommercialBypass, '_find_all_mapping_candidates',
                        lambda *a, **kw: [inverse])
    assert n._decrypt_blob_if_encrypted('unused', encrypted, pe_data=b'PE') == plain


def test_plain_frame_at_section_start_and_unaligned_length():
    _, plain, _ = _sample()
    section = types.SimpleNamespace(offset=0, size=len(plain), addr=0x1000)
    img = types.SimpleNamespace(data=plain, sections=[section], fmt='elf')
    result = n.find_blob(img)
    assert result is not None and result[0] == 0x1000 and result[1] == plain


def test_commercial_resource_in_ndx(monkeypatch):
    payload, plain, encrypted = _sample()
    entry = types.SimpleNamespace(OffsetToData=0, Size=len(encrypted))
    lang = types.SimpleNamespace(data=types.SimpleNamespace(struct=entry))
    name = types.SimpleNamespace(id=3, directory=types.SimpleNamespace(entries=[lang]))
    typ = types.SimpleNamespace(id=10, directory=types.SimpleNamespace(entries=[name]))
    fake_pe = types.SimpleNamespace(DIRECTORY_ENTRY_RESOURCE=types.SimpleNamespace(entries=[typ]))
    section = types.SimpleNamespace(offset=0, size=len(encrypted), addr=0x1000)
    img = types.SimpleNamespace(data=encrypted, sections=[section], fmt='pe',
                                _pe=fake_pe, base=0x1000, path='unused',
                                va_to_off=lambda va: va - 0x1000)
    monkeypatch.setattr(pefile, 'PE', lambda **kw: object())
    result = n.find_blob(img)
    assert result == (0x1000, plain, len(payload)) and img._ndx_commercial_blob


def test_static_initialized_table_without_target_execution():
    payload, plain, framed = _sample('other salt')
    encrypted = framed[8:]
    forward = list(range(256))
    random.Random('other salt').shuffle(forward)
    inverse = [0] * 256
    for i, v in enumerate(forward):
        inverse[v] = i
    image = bytearray(0xa000)
    loader = bytearray()
    def relative(opcode, address):
        start = 0x1000 + len(loader)
        loader.extend(opcode + struct.pack('<i', address - start - len(opcode) - 4))
    relative(b'\x48\x8d\x1d', 0x5000)  # input buffer
    relative(b'\xe8', 0x2000)             # table initializer
    relative(b'\x4c\x8d\x15', 0x9000)  # substitution table
    loader.extend(b'\x49\x83\xf9\x10\x83\xe1\x07\x48\x31\xc2')
    loader.extend(b'\x0f\xb6\x03\x41\x0f\xb6\x02')
    loader.extend(b'\x49\x83\xc0\x0a\x49\x81\xf8' + struct.pack('<I', len(encrypted) * 10))
    relative(b'\x48\x8d\x0d', 0x3000)  # .bytecode xref
    loader.append(0xc3)
    image[0x1000:0x1000 + len(loader)] = loader
    initializer = bytearray()
    for index, value in enumerate(inverse):
        here = 0x2000 + len(initializer)
        initializer.extend(b'\xc6\x05' + struct.pack('<i', 0x9000 + index - here - 7) + bytes([value]))
    initializer.append(0xc3)
    image[0x2000:0x2000 + len(initializer)] = initializer
    image[0x3000:0x300a] = b'.bytecode\0'
    image[0x5000:0x5000 + len(encrypted)] = encrypted
    pdata = types.SimpleNamespace(Name=b'.pdata\0\0', get_data=lambda: struct.pack('<III', 0x1000, 0x1000 + len(loader), 1))
    pe = types.SimpleNamespace(sections=[pdata], get_data=lambda rva, size: bytes(image[rva:rva + size]))
    section = types.SimpleNamespace(offset=0, size=len(image), addr=0)
    img = types.SimpleNamespace(fmt='pe', _pe=pe, data=bytes(image), sections=[section], base=0,
                                is_exec=lambda address: True, off_to_va=lambda off: off,
                                va_to_off=lambda va: va)
    result = n._ndx_static_initialized_blob(img)
    assert result == (0x5000 - 8, plain, len(payload))
    image[0x5000] ^= 1
    img.data = bytes(image)
    assert n._ndx_static_initialized_blob(img) is None


def test_code_flags_without_qualname_field(monkeypatch):
    profile = {'fields': {'qualname': None, 'free_vars': 18, 'kw_only': 28, 'pos_only': 12},
               'gen_mask': 3, 'gen_values': {0: 0, 1: 0x20, 2: 0x80, 3: 0x200},
               'result_masks': [(4, 1), (8, 2), (16, 4), (32, 8)]}
    monkeypatch.setattr(n, '_CURRENT_NUITKA_MARKER_MAP', {1: ord('C')})
    monkeypatch.setattr(n, '_CURRENT_NUITKA_CODE_FLAGS', profile)
    assert n._native_code_flag_profile() == profile
    assert n._parse_native_code_optionals(b'', 0, 0, 'func', profile) == ('func', (), 0, 0, 0)
    invalid = dict(profile, fields=dict(profile['fields'], free_vars=None))
    monkeypatch.setattr(n, '_CURRENT_NUITKA_CODE_FLAGS', invalid)
    with pytest.raises(n._NuitkaDecoderAbort):
        n._native_code_flag_profile()


def test_constants_slots_use_statically_proven_base():
    analyzer = object.__new__(n.ModuleCodeAnalyzer)
    analyzer.img = types.SimpleNamespace(_ndx_static_constants_bases={'module': 0x1008},
                                         _ndx_static_global_base=0x2000)
    analyzer.module = types.SimpleNamespace(name='module', func_ptr=0x4000,
                                            consts=['first', 'second'],
                                            global_consts=['shared'])
    analyzer.const_slots = {}
    analyzer._ndx_constants_scan_key = None
    analyzer._ndx_constants_scan_result = None
    analyzer.mod_consts_base = analyzer.global_base = analyzer.load_blob_va = None
    assert analyzer.find_constants_arrays() == 0x1008
    assert analyzer.const_slots == {0x1008: ('priv', 0), 0x1010: ('priv', 1),
                                    0x2000: ('glob', 0)}


def test_native_matching_with_optional_pe_fixture(monkeypatch):
    path = os.environ.get('NDX_STATIC_PE_FIXTURE')
    if not path:
        pytest.skip('set NDX_STATIC_PE_FIXTURE to an initialized-table PE fixture')
    image = n.BinaryImage(Path(path).read_bytes(), path)
    blob = n._ndx_static_initialized_blob(image)
    assert blob is not None
    chunks = n.parse_blob_modules(blob[1], strict=True)
    matched = n._ndx_static_module_bodies(image, chunks)
    assert matched
    by_name = dict(chunks)
    evidence = {record['name']: record for record in image._ndx_static_module_evidence}
    assert image._ndx_static_constants_bases
    for entry in matched:
        record = evidence[entry.name]
        assert image.is_exec(entry.func_ptr)
        assert record['func_ptr'] == entry.func_ptr
        assert record['pool_sha256'] == hashlib.sha256(by_name[entry.name]).hexdigest()
        if record['constants_base'] is not None:
            assert image.is_data(record['constants_base'])
            assert image._ndx_static_constants_bases[entry.name] == record['constants_base']
    profile = n._ndx_discover_310_constants(image, chunks, (3, 10))
    assert profile is not None
    monkeypatch.setattr(n, '_CURRENT_NUITKA_MARKER_MAP', profile['markers'])
    monkeypatch.setattr(n, '_CURRENT_NUITKA_FLOAT_SELECTOR_MAP', profile['float_selectors'])
    monkeypatch.setattr(n, '_CURRENT_NUITKA_CODE_FLAGS', profile['code_flags'])
    monkeypatch.setattr(n, '_CURRENT_NUITKA_TERMINATOR', profile['terminator'])
    shared = n.parse_module_constants(by_name[''], python_version=(3, 10), profile='modern_vlq31')
    assert shared.diagnostics['exact']
    proven_maker = None
    for entry in matched[:20]:
        private = n.parse_module_constants(by_name[entry.name], python_version=(3, 10), profile='modern_vlq31')
        if not private.diagnostics['exact'] or entry.name not in image._ndx_static_constants_bases:
            continue
        module = types.SimpleNamespace(name=entry.name, func_ptr=entry.func_ptr,
                                       consts=private, global_consts=shared)
        analyzer = n.ModuleCodeAnalyzer(image, module, None)
        analyzer.find_constants_arrays()
        for ins in analyzer.fd.insns(entry.func_ptr, max_bytes=0x20000, stop_at_ret=False):
            if ins.mnemonic != 'call':
                continue
            destination = n.is_imm(ins.op_str)
            if destination is None or not image.is_exec(destination):
                continue
            proven_maker = analyzer._decode_function_maker(destination)
            if proven_maker and proven_maker.get('impl_va') and image.is_exec(proven_maker['impl_va']):
                break
            proven_maker = None
        if proven_maker:
            break
    assert proven_maker and image.is_exec(proven_maker['impl_va'])
