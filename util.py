from enum import Enum
from constant import *

# Diagram Packet

# ID: unique indentifier per paket (8bit)
# Sequence number: urutan paket pada id yang sama (16bit)
# Length: panjang section data, max 65536 char, unsigned int (16bit)
# Checksum: xor seluruh paket setiap 2 byte (16bit)
# Data: data akhir diberi type FIN, max(64KB, 65536 byte)


def generate_checksum(data_header, file_data):
    temp_packet = data_header[:]
    temp_packet += file_data
    checksum = 0
    for i in range(0, len(temp_packet), 2):
        checksum ^= int.from_bytes(data_header[i:i + 2], byteorder=BYTE_ORDER)
    return checksum.to_bytes(LENGTH_CHECKSUM, byteorder=BYTE_ORDER)


def create_packet(file_data, id, sequence, packet_type):
    packet = bytearray()

    type_id = packet_type.value << 4 | id
    packet.append(type_id)
    packet += sequence.to_bytes(LENGTH_LENGTH, byteorder=BYTE_ORDER)
    packet += (len(file_data)).to_bytes(LENGTH_LENGTH, byteorder=BYTE_ORDER)

    checksum = generate_checksum(packet, file_data)
    packet += checksum

    packet += file_data

    return packet


def to_int(byte):
    return int.from_bytes(byte, byteorder=BYTE_ORDER)


def parse_packet(packet):
    data_ID_type = packet[INDEX_TYPE_ID:INDEX_TYPE_ID + LENGTH_TYPE_ID]
    data_type = to_int(data_ID_type) >> 4
    data_ID = to_int(data_ID_type) & 0x0f

    data_sequence = to_int(packet[INDEX_SEQUENCE:INDEX_SEQUENCE +
                                  LENGTH_SEQUENCE])

    data_length = to_int(packet[INDEX_LENGTH:INDEX_LENGTH + LENGTH_LENGTH])

    file_data = packet[INDEX_DATA:INDEX_DATA + data_length]

    data_checksum = packet[INDEX_CHECKSUM:INDEX_CHECKSUM + LENGTH_CHECKSUM]
    data_header = packet[INDEX_TYPE_ID:INDEX_CHECKSUM]
    checksum = generate_checksum(data_header, file_data)

    if checksum == data_checksum:
        return {
            "file_data": file_data,
            "id": data_ID,
            "sequence": data_sequence,
            "type": data_type
        }
    else:
        return {"type": PacketType.INVALID}