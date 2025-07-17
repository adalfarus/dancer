"""Storage links to aplustools"""
from aplustools.data.bintools import (encode_float, decode_float, encode_integer, decode_integer, bit_length,
                                      bytes_length, get_variable_bytes_like, read_variable_bytes_like,
                                      expected_varint_length_bytecount, BitBuffer, set_bits, bits,
                                      bytes_to_human_readable_binary_iec, bytes_to_human_readable_decimal_si,
                                      bits_to_human_readable)
from aplustools.data.dummy import Dummy3 as Dummy
from aplustools.data.storage import JSONStorage, SQLite3Storage, BinaryStorage

__all__ = ["encode_float", "decode_float", "encode_integer", "decode_integer", "bit_length", "bytes_length",
           "get_variable_bytes_like", "read_variable_bytes_like", "expected_varint_length_bytecount", "BitBuffer",
           "set_bits", "bits", "bytes_to_human_readable_binary_iec", "bytes_to_human_readable_decimal_si",
           "bits_to_human_readable", "Dummy", "JSONStorage", "SQLite3Storage", "BinaryStorage"]
