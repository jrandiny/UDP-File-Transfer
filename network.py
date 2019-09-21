import socket
import threading
import time
from constant import *
from queue import Queue
from util import parse_packet, create_packet
from math import ceil

thread_pool_listener = dict()
thread_pool_sender = dict()


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
            print("Mendapat addr {}".format(addr))
            print(threading.activeCount())
            packet_data = parse_packet(data)
            ''' 
                1. Ambil type
                2. Jika valid, ambil addr dan id,
                3. Jika id belum pernah diambil, buat thread baru
                4. Jika sudah ada idnya, oper ke thread
            '''

            data_type = PacketType(packet_data["type"])
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
                                         args=(data_ID, addr,
                                               handler)).start()
                        handler.put(packet_data)
                    else:
                        handler.put(packet_data)
                else:
                    thread_pool_sender[source_address][data_ID].put(
                        packet_data)

        except socket.error:
            pass
    listener_socket.close()


def send(file, addr, port):
    '''
        1. Pecah file
        2. Buat jadi packet
        3. Buat id baru, dan thread baru
    '''
    # check addr di thread_pool_sender
    if thread_pool_sender.get(addr) == None:
        # tidak ada, bikin baru
        thread_pool_sender[addr] = [None] * 16
    # thread_pool_sender[addr] ada
    thread_pool = thread_pool_sender[addr]
    # check empty thread
    id = 0
    while thread_pool[id] != None:
        id += 1
    # ada thread[id] kosong
    max_number_send = ceil(len(file) / MAX_LENGTH_DATA)
    last_sequence = 0
    thread_pool[id] = Queue()
    array_packet = []
    for sequence in range(max_number_send - 1):
        start_idx = sequence * MAX_LENGTH_DATA
        packet = create_packet(file[start_idx:start_idx + MAX_LENGTH_DATA], id,
                               sequence, PacketType.DATA)
        array_packet.append(packet)
        last_sequence = sequence + 1

    # kirim packet terakhir
    start_idx = last_sequence * MAX_LENGTH_DATA
    packet = create_packet(file[start_idx:start_idx + MAX_LENGTH_DATA], id,
                           last_sequence, PacketType.FIN)
    array_packet.append(packet)

    threading.Thread(target=send_thread,
                     args=(id, (addr, port), thread_pool[id],
                           array_packet)).start()


def send_thread(id, addr, input_queue: Queue, data):
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    finished = False
    index = 0

    while not finished:
        send_socket.sendto(data[index], addr)

        fin_package = False
        if (index == len(data) - 1):
            fin_package = True

        start_wait = time.time()
        ack_received = False

        while (time.time() - start_wait >= MAX_WAIT_ACK) or ack_received:
            if (not input_queue.empty()):
                ack_packet = input_queue.get()
                if (ack_packet["id"] == id) and (
                        ack_packet["sequence"] == index):
                    if (ack_packet["type"] == PacketType.ACK):
                        ack_received = True
                        index += 1
                    elif (ack_packet["type"] == PacketType.FIN_ACK
                          ) and fin_package:
                        ack_received = True
                        finished = True
                input_queue.task_done()

    thread_pool_sender[addr[0]][id] = None
    send_socket.close()


def receive_thread(id, addr, input_queue):
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    file_data = bytearray()
    iter = 0
    finished = False
    while not finished:
        elm = input_queue.get()
        data = elm["data"]
        data_id = elm["id"]
        data_type = elm["type"]
        data_sequence = elm["sequence"]
        # send feedback
        if data_type == PacketType.DATA:
            feedback_packet = create_packet(bytearray(), data_id,
                                            data_sequence, PacketType.ACK)
        else:
            # fin
            feedback_packet = create_packet(bytearray(), data_id,
                                            data_sequence, PacketType.FIN_ACK)
        send_socket.sendto(feedback_packet, addr)
        # asumsi sequence urut
        file_data.append(data)
        if data_type == PacketType.FIN:
            # data berakhir
            finished = True
        input_queue.task_done()

    thread_pool_sender[addr[0]][id] = None
    send_socket.close()