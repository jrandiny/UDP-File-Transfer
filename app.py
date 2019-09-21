import threading
from network import listener, send

if __name__ == "__main__":
    port = int(input("Port : "))
    thread_quit = threading.Event()

    network_thread = threading.Thread(target=listener,
                                      args=(thread_quit, port))
    network_thread.start()

    while True:
        input("aa")
        with open("util.py", "rb") as binary_file:
            send(binary_file.read(), "127.0.0.1", port)
        input()
        # user_input = input("> ")
        # input_list = user_input.split(" ")

        # if (input_list[0] == "send"):
        #     with open(input_list[1], "rb") as binary_file:
        #         send(binary_file.read(), input_list[2], port)
        # elif (input_list[0] == "quit"):
        #     break
        # else:
        #     print("Invalid input")

    thread_quit.set()
    network_thread.join()
