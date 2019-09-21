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
    # data_header.append(file_data)
    checksum = b'\x00\x00'
    # for i in range(0, len(temp_packet), 2):
    #     #     first = temp_packet[i]
    #     #     second = temp_packet[i + 1]#
    #     # checksum ^= data_header[i:i + 2]
    #     checksum = bitwise(
    #         checksum,
    #         "^",
    #     )
    return checksum


def create_packet(file_data, id, sequence, packet_type):
    packet = bytearray()

    type_id = packet_type.value << 4 | id
    packet.append(type_id)
    packet += sequence.to_bytes(LENGTH_LENGTH, byteorder='big')
    packet += (len(file_data)).to_bytes(LENGTH_LENGTH, byteorder='big')

    checksum = generate_checksum(packet, file_data)
    packet += checksum  # # print(str(packet))

    packet += file_data
    # for data in checksum:
    #     packet.append(data)
    # for data in file_data:
    #     packet.append(data)

    return packet


def parse_packet(packet):
    data_ID_type = packet[INDEX_TYPE_ID:INDEX_TYPE_ID + LENGTH_TYPE_ID]
    data_type = bitwise(data_ID_type, ">>", 4)
    data_ID = bitwise(data_ID_type, '&', b'\x0f')
    data_sequence = packet[INDEX_SEQUENCE:INDEX_SEQUENCE + LENGTH_SEQUENCE]
    data_length = packet[INDEX_LENGTH:INDEX_LENGTH + LENGTH_LENGTH]
    file_data = packet[INDEX_DATA:INDEX_DATA + data_length[0]]
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


def bitwise(input_1, operator, input_2):
    if operator == '&':
        return bytes(input_1[0] & input_2[0])
    elif operator == '|':
        return bytes(input_1[0] | input_2[0])
    elif operator == '<<':
        return bytes(input_1[0] << input_2)
    elif operator == '>>':
        return bytes(input_1[0] >> input_2)
    elif operator == '^':
        return bytes(input_1[0] ^ input_2[0])
