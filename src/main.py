import sys
from ui import start_client_gui
from server import Server


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        start_client_gui()
    elif len(sys.argv) > 1 and sys.argv[1] == "server":
        server = Server(server_id="stgserver", port=6161)
        server.start()
    else:
        print("Usage: python main.py [client|server]")
        sys.exit(1)


if __name__ == "__main__":
    main()