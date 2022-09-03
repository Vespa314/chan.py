import sys

from tools import send_msg

if __name__ == "__main__":
    send_msg(sys.argv[1], sys.argv[2], lv='NOTIFY')
