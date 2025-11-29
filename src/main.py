import sys
from ui import start_client_gui


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        start_client_gui()
    elif len(sys.argv) > 1 and sys.argv[1] == "server":
        # TODO: Start server
        print("Server mode - to be implemented")
    else:
        print("Usage: python main.py [client|server]")
        sys.exit(1)


if __name__ == "__main__":
    main()