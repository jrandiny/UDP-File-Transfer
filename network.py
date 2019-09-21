import socket
import threading
import time
import uuid
import os
from constant import *
from queue import Queue
from util import parse_packet, create_packet
from math import ceil

thread_pool_listener = dict()
thread_pool_sender = dict()

listener_lock = threading.Lock()


def listener(thread_quit, port):
    listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener_socket.setblocking(False)
    listener_socket.bind(("", port))
    while (not thread_quit.is_set()):
        try:
            data, addr = listener_socket.recvfrom(MAX_LENGTH_DATA +
                                                  LENGTH_TYPE_ID +
                                                  LENGTH_CHECKSUM +
                                                  LENGTH_LENGTH +
                                                  LENGTH_SEQUENCE)

            packet_data = parse_packet(data)

            data_type = PacketType(packet_data["type"])
            # print(data_type)
            if data_type != PacketType.INVALID:
                source_address = addr[0]
                data_ID = packet_data["id"]

                if data_type == PacketType.DATA or data_type == PacketType.FIN:
                    if thread_pool_listener.get(source_address) == None:
                        thread_pool_listener[source_address] = [None] * 16

                    if thread_pool_listener[source_address][data_ID] == None:
                        handler = Queue()
                        thread_pool_listener[source_address][data_ID] = handler
                        threading.Thread(target=receive_thread,
                                         args=((source_address, port),
                                               handler)).start()
                        handler.put(packet_data)
                    else:
                        thread_pool_listener[source_address][data_ID].put(
                            packet_data)
                else:
                    if (thread_pool_sender[source_address][data_ID] != None):
                        thread_pool_sender[source_address][data_ID].put(
                            packet_data)

        except socket.error:
            pass
    listener_socket.close()


def send(file, addr, port, size):
    # Check addr di thread_pool_sender
    if thread_pool_sender.get(addr) == None:
        # tidak ada, bikin baru
        thread_pool_sender[addr] = [None] * 16

    # Assert : thread_pool_sender[addr] ada
    thread_pool = thread_pool_sender[addr]

    # check empty thread
    thread_id = 0
    while thread_pool[thread_id] != None:
        thread_id += 1

    # Assert : ada thread[thread_id] kosong
    packet_queue = Queue()

    max_number_send = ceil(size / MAX_LENGTH_DATA)
    last_sequence = 0
    thread_pool[thread_id] = Queue()

    threading.Thread(target=send_thread,
                     args=(
                         thread_id,
                         (addr, port),
                         thread_pool[thread_id],
                         packet_queue,
                         max_number_send,
                     )).start()

    for sequence in range(max_number_send - 1):
        start_idx = sequence * MAX_LENGTH_DATA
        packet = create_packet(file.read(MAX_LENGTH_DATA), thread_id, sequence,
                               PacketType.DATA)
        packet_queue.put(packet)
        packet_queue.join()
        last_sequence = sequence + 1

    # kirim packet terakhir
    start_idx = last_sequence * MAX_LENGTH_DATA
    packet = create_packet(file.read(MAX_LENGTH_DATA), thread_id,
                           last_sequence, PacketType.FIN)
    packet_queue.put(packet)


def send_thread(packet_id, addr, input_queue, data, packet_count):
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    finished = False
    index = 0

    ack_received = True

    try:
        while not finished:

            if ack_received:
                current_package = data.get()

            send_socket.sendto(current_package, addr)

            fin_package = False
            if (index == packet_count - 1):
                fin_package = True

            start_wait = time.time()

            ack_received = False

            while (time.time() - start_wait <=
                   MAX_WAIT_ACK) and not ack_received:
                if (not input_queue.empty()):
                    ack_packet = input_queue.get()
                    if (ack_packet["id"] == packet_id) and (
                            ack_packet["sequence"] == index):
                        packet_type = PacketType(ack_packet["type"])
                        if (packet_type == PacketType.ACK):
                            ack_received = True
                            index += 1
                        elif (packet_type == PacketType.FIN_ACK
                              ) and fin_package:
                            ack_received = True
                            finished = True
                    input_queue.task_done()

            if ack_received:
                data.task_done()

    except socket.gaierror:
        print("Connection error (is destination up?)\n> ", end="")

    thread_pool_sender[addr[0]][packet_id] = None
    send_socket.close()


def receive_thread(addr, input_queue):
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("Receiving file from {}\n> ".format(addr[0]), end="")

    last_sequence = -1
    finished = False

    file_uuid = uuid.uuid4().hex

    with open(file_uuid, "wb") as binary_file:
        while not finished:
            elm = input_queue.get()
            data = elm["file_data"]
            data_id = elm["id"]
            data_type = PacketType(elm["type"])
            data_sequence = elm["sequence"]
            # send feedback
            if data_type == PacketType.DATA:
                feedback_packet = create_packet(bytearray(), data_id,
                                                data_sequence, PacketType.ACK)
            else:
                # fin
                feedback_packet = create_packet(bytearray(), data_id,
                                                data_sequence,
                                                PacketType.FIN_ACK)

            send_socket.sendto(feedback_packet, addr)

            if (data_sequence == last_sequence + 1):
                binary_file.write(data)
                last_sequence = data_sequence

                if data_type == PacketType.FIN:
                    finished = True
            input_queue.task_done()

        thread_pool_listener[addr[0]][data_id] = None
        send_socket.close()

    os.rename(file_uuid, "Received_{}_{}".format(addr[0], data_id))

    print("File received from {}\n> ".format(addr[0]), end="")
