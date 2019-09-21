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

MAX_LENGTH_DATA = 32768

MAX_WAIT_ACK = 0.1

BYTE_ORDER = 'big'


class PacketType(Enum):
    # type paket yang dikirim (8bit)
    DATA = 0  # berdata
    ACK = 1  # feedback jika diterima
    FIN = 2  # berdata
    FIN_ACK = 3  # feedback jika semua diterima
    INVALID = 4
