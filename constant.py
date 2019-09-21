from enum import Enum

INDEX_TYPE_ID = 0
INDEX_SEQUENCE = 1
INDEX_LENGTH = 3
INDEX_CHECKSUM = 5
INDEX_DATA = 7

LENGTH_TYPE_ID = 1
LENGTH_SEQUENCE = 2
LENGTH_LENGTH = 2
LENGTH_CHECKSUM = 2

MAX_LENGTH_DATA = 65536


class PacketType(Enum):
    # type paket yang dikirim (8bit)
    DATA = 0x0  # berdata
    ACK = 0x1  # feedback jika diterima
    FIN = 0x2  # berdata
    FIN_ACK = 0x3  # feedback jika semua diterima
    INVALID = 0x4
