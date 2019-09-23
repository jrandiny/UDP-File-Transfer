import threading
import os
import network


def send_worker(file_name, destination, size):
    with open(input_list[1], "rb") as binary_file:
        network.send(binary_file, destination, port, size, file_name)


if __name__ == "__main__":
    port = int(input("Input listener port : "))
    thread_quit = threading.Event()

    network_thread = threading.Thread(target=network.listener,
                                      args=(thread_quit, port))
    network_thread.start()

    while True:
        user_input = input("\r> ")
        input_list = user_input.split(" ")

        if (input_list[0] == "send"):
            try:
                file_stat = os.stat(input_list[1])
                threading.Thread(target=send_worker,
                                 args=(input_list[1], input_list[2],
                                       file_stat.st_size)).start()
                print("Sending file to {}".format(input_list[2]))
                network.file_count += 1
                network.current_progress += 1
            except FileNotFoundError:
                print("File not found")
        elif (input_list[0] == "help"):
            print("Avaiable command : ")
            print("-------------------")
            print("send <file> <ip>")
            print("show -- to show progress bar")
            print("<enter> -- to hide progress bar")
        elif (input_list[0] == "show"):
            if network.file_count > 0:
                network.show_progress = True
            else:
                print("No file transfer happening")

        elif (input_list[0] == "quit"):
            break
        elif len(user_input) == 0:
            network.show_progress = False
        else:
            print("Invalid input")

    thread_quit.set()
    network_thread.join()
