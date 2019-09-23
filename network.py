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

show_progress = False
file_count = 0
current_progress = 0
total_progress = 0


def listener(thread_quit, port):
    '''
    Fungsi utama yang mendengarkan semua pesan masuk
    Exclusive access ke port yang diatur

    Args:
        thread_quit (threading.Event) : Signaling untuk memberitahu jika thread selesai
        port (int) : Port number untuk dibind
    '''

    # Setup socket
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
            data_type = packet_data["type"]

            if data_type != PacketType.INVALID:
                source_address = addr[0]
                data_ID = packet_data["id"]

                # Jika Data atau FIN buat thread listener, jika tidak passing ke thread sender
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


def send(file, ip_address, port, size, file_name):
    '''
    Fungsi utama mengirim file.
    Bertanggung jawab untuk memecah file dan memberikannya pada sender

    Args:
        file (BufferedReader) : Reader untuk file yang ingin dikirim
        ip_address (str) : String berisi alamat ip tujuan
        port (int) : Port tujuan
        size (int) : Ukuran file (untuk menghitung kapan FIN)
    '''
    global total_progress
    global file_count
    global current_progress

    # Setup thread pool jika belum ada
    if thread_pool_sender.get(ip_address) == None:
        thread_pool_sender[ip_address] = [None] * 16

    thread_pool = thread_pool_sender[ip_address]

    # Cari thread id kosong
    thread_id = 0
    while thread_pool[thread_id] != None:
        thread_id += 1

    # Assert : ada thread[thread_id] kosong
    max_number_send = ceil(size / MAX_LENGTH_DATA) + 1

    total_progress += max_number_send
    thread_pool[thread_id] = Queue()

    # Setup sender thread
    packet_queue = Queue()
    threading.Thread(target=send_thread,
                     args=(
                         thread_id,
                         (ip_address, port),
                         thread_pool[thread_id],
                         packet_queue,
                         max_number_send,
                     )).start()

    # Buat paket data
    packet = create_packet(file_name.encode(), thread_id, 0, PacketType.DATA)
    packet_queue.put(packet)

    packet_queue.join()

    last_sequence = 1

    for sequence in range(last_sequence, max_number_send - 1):
        packet = create_packet(file.read(MAX_LENGTH_DATA), thread_id, sequence,
                               PacketType.DATA)
        packet_queue.put(packet)

        packet_queue.join()
        last_sequence = sequence + 1

    # Kirim FIN
    packet = create_packet(file.read(MAX_LENGTH_DATA), thread_id,
                           last_sequence, PacketType.FIN)
    packet_queue.put(packet)
    packet_queue.join()


def send_thread(packet_id, addr, input_queue, file_queue, packet_count):
    '''
    Thread yang bertanggung jawab terhadap pengiriman
    Bertanggung jawab untuk:
        - Mengirim file
        - Mengirim kembali file jika ACK tidak diterima dalam sekian waktu
    
    Args:
        packet_id (int) : ID paket
        addr ((str,int)) : Tuple berisi alamat dan port 
        input_queue (Queue) : Queue untuk input paket ACK dan FIN-ACK
        file_queue (Queue) : Queue berisi paket yang ingin dikirim
        packet_count (int) : Berisi jumlah paket untuk deteksi kapan fin
    '''
    global current_progress
    global file_count
    global total_progress
    global show_progress

    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    finished = False
    index = 0

    ack_received = True

    try:
        while not finished:
            # ack_received True saat siap mengirim paket baru (saat yang sebelumnya sudah ACK)
            if ack_received:
                current_package = file_queue.get()

            send_socket.sendto(current_package, addr)

            fin_package = (index == packet_count - 1)

            start_wait = time.time()

            ack_received = False

            while (time.time() - start_wait <=
                   MAX_WAIT_ACK) and not ack_received:
                if (not input_queue.empty()):
                    ack_packet = input_queue.get()
                    if (ack_packet["id"] == packet_id) and (
                            ack_packet["sequence"] == index):
                        packet_type = ack_packet["type"]
                        if (packet_type == PacketType.ACK):
                            ack_received = True
                            index += 1
                            current_progress += 1
                        elif (packet_type == PacketType.FIN_ACK
                              ) and fin_package:
                            ack_received = True
                            finished = True
                    input_queue.task_done()

            if ack_received:
                file_queue.task_done()

            if show_progress:
                printProgress(current_progress, total_progress)
    except socket.gaierror:
        print("Connection error (is destination up?)\n> ", end="")

    thread_pool_sender[addr[0]][packet_id] = None
    send_socket.close()
    file_count -= 1
    print("\nFile sent to {}\n> ".format(addr), end="")
    if file_count == 0:
        current_progress = total_progress = 0
        show_progress = False


def receive_thread(addr, input_queue):
    '''
    Thread yang bertanggung jawab terhadap penerimaan
    Bertanggung jawab untuk:
        - Menerima paket data
        - Mengirim ACK
    
    Args:
        addr ((str,int)) : Tuple berisi alamat dan port pengirim
        input_queue (Queue) : Queue untuk input paket DATA dan FIN
    '''
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("Receiving file from {}\n> ".format(addr[0]), end="")

    last_sequence = -1
    finished = False

    file_uuid = uuid.uuid4().hex
    file_name = ""

    with open(file_uuid, "wb") as binary_file:
        while not finished:
            elm = input_queue.get()
            data = elm["file_data"]
            data_id = elm["id"]
            data_type = elm["type"]
            data_sequence = elm["sequence"]

            # send feedback
            if data_type == PacketType.DATA:
                feedback_packet = create_packet(bytearray(), data_id,
                                                data_sequence, PacketType.ACK)
            else:
                feedback_packet = create_packet(bytearray(), data_id,
                                                data_sequence,
                                                PacketType.FIN_ACK)

            send_socket.sendto(feedback_packet, addr)

            # Pastikan sequence urutan
            if (data_sequence == last_sequence + 1):
                if (data_sequence == 0):
                    file_name = data.decode()
                    last_sequence = data_sequence
                else:
                    binary_file.write(data)
                    last_sequence = data_sequence

                    if data_type == PacketType.FIN:
                        finished = True

            input_queue.task_done()

        thread_pool_listener[addr[0]][data_id] = None
        send_socket.close()
    print(file_name)
    os.rename(file_uuid, file_name)

    print("File {} received from {}\n> ".format(file_name, addr[0]), end="")


def printProgress(current, total, decimals=2, length=50, fill='='):
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (current / float(total)))
    filledLength = int(length * current // total) - 1
    bar = fill * filledLength + '>' + '-' * (length - filledLength - 1)
    print('\r%s [%s] %s%%' %
          ('Sending ' + str(file_count) + ' file(s)', bar, percent),
          end='\r')
