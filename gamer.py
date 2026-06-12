#!/usr/bin/env python3
# POTATO ULTIMATE - Xbox Fortnite IP + Gamertag Mapper
# Run as Administrator on Windows 11
# NO MANUAL CONFIG NEEDED - IT JUST WORKS

import os
import sys
import subprocess
import threading
import time
import re
import socket
import json
from datetime import datetime
from collections import defaultdict

# ========== AUTO-INSTALL MISSING PACKAGES ==========
def auto_install_packages():
    packages = ['scapy', 'colorama', 'psutil', 'requests']
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"[*] Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'])

auto_install_packages()

from scapy.all import sniff, IP, UDP, Ether, ARP, srp, Raw, IPv6
from scapy.arch.windows import get_windows_if_list
from colorama import init, Fore, Back, Style
import psutil
import requests

init(autoreset=True)

# ========== GLOBAL DATABASE ==========
peer_database = defaultdict(lambda: {
    "gamertag": "🔍 Scanning...",
    "packets": 0,
    "first_seen": None,
    "last_seen": None,
    "ports": set(),
    "city": "Unknown",
    "country": "Unknown",
    "isp": "Unknown"
})

stop_sniffing = threading.Event()
xbox_ip = None
xbox_mac = None

# ========== AUTO-DETECT XBOX ON NETWORK ==========
def auto_detect_xbox():
    global xbox_ip, xbox_mac
    print(f"{Fore.CYAN}[1/5] Scanning network for Xbox Series S...{Style.RESET_ALL}")
    
    # Get local network range
    local_ip = socket.gethostbyname(socket.gethostname())
    subnet = '.'.join(local_ip.split('.')[:-1]) + '.1/24'
    
    # ARP scan for Xbox manufacturer (Microsoft)
    arp_request = ARP(pdst=subnet)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = broadcast / arp_request
    answered = srp(packet, timeout=3, verbose=False)[0]
    
    for sent, received in answered:
        mac = received.hwsrc.upper()
        # Microsoft MAC prefixes: 00:15:5D, 00:1A:6B, 00:1D:D8, 08:00:27, 28:18:78, 4C:72:B9, 70:4D:7B, 88:51:FB
        if any(prefix in mac for prefix in ["00:15:5D", "00:1A:6B", "4C:72:B9", "70:4D:7B", "88:51:FB"]):
            xbox_ip = received.psrc
            xbox_mac = mac
            print(f"{Fore.GREEN}✓ Xbox detected! IP: {xbox_ip} | MAC: {xbox_mac}{Style.RESET_ALL}")
            return True
    
    # Fallback: ask user for IP if auto-detect fails
    print(f"{Fore.YELLOW}⚠ Auto-detect failed. Enter Xbox IP manually (or press Enter to retry):{Style.RESET_ALL}")
    manual_ip = input("> ").strip()
    if manual_ip:
        xbox_ip = manual_ip
        # Get MAC from ARP table
        result = subprocess.run(f"arp -a {xbox_ip}", capture_output=True, text=True, shell=True)
        for line in result.stdout.split('\n'):
            if xbox_ip in line:
                parts = line.split()
                if len(parts) >= 2:
                    xbox_mac = parts[1].upper()
                    print(f"{Fore.GREEN}✓ MAC found: {xbox_mac}{Style.RESET_ALL}")
                    return True
        return False
    return False

# ========== IP GEOLOCATION ==========
def get_ip_geolocation(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('city', 'Unknown'), data.get('countryCode', 'Unknown'), data.get('isp', 'Unknown')
    except:
        pass
    return "Unknown", "Unknown", "Unknown"

# ========== EXTRACT GAMERTAG FROM PACKET ==========
def extract_gamertag(packet):
    if Raw not in packet:
        return None
    
    raw_data = bytes(packet[Raw].load)
    
    # Try multiple encodings
    encodings = ['utf-16le', 'utf-8', 'utf-16be', 'latin1']
    for encoding in encodings:
        try:
            decoded = raw_data.decode(encoding, errors='ignore')
            # Xbox Gamertag pattern: 3-15 chars, alphanumeric, spaces, underscores
            matches = re.findall(r'([A-Za-z0-9 _-]{3,15})', decoded)
            for match in matches:
                match = match.strip()
                # Filter out junk
                if len(match) >= 3 and not match.isdigit() and match not in ["Xbox", "Live", "Microsoft", "Teredo", "STUN", "UDP", "TCP", "HTTP", "Epic", "Fortnite", "Game", "Party", "Chat", "Voice"]:
                    if not any(x in match.lower() for x in ["xbox", "microsoft", "windows", "server", "client"]):
                        return match
        except:
            continue
    return None

# ========== PACKET CAPTURE CALLBACK ==========
def packet_callback(packet):
    global xbox_ip
    
    if Ether not in packet:
        return
    
    # Filter by Xbox MAC if we have it
    if xbox_mac and packet[Ether].src.lower() != xbox_mac.lower():
        return
    
    # Handle IPv4 and IPv6
    remote_ip = None
    if IP in packet:
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        local_ip = socket.gethostbyname(socket.gethostname())
        
        if src_ip == xbox_ip or (xbox_ip and src_ip == xbox_ip):
            remote_ip = dst_ip
        elif dst_ip == xbox_ip or (xbox_ip and dst_ip == xbox_ip):
            remote_ip = src_ip
        else:
            return
    
    if IPv6 in packet:
        src_ip = packet[IPv6].src
        dst_ip = packet[IPv6].dst
        if src_ip == xbox_ip:
            remote_ip = dst_ip
        elif dst_ip == xbox_ip:
            remote_ip = src_ip
    
    if not remote_ip:
        return
    
    # Filter out local IPs
    if remote_ip.startswith(('192.168.', '10.', '172.', '127.', '169.254.')):
        return
    
    # Filter out known Epic/Microsoft servers
    server_prefixes = ('34.', '52.', '99.', '13.', '20.', '40.', '54.', '143.', '3.', '18.', '35.')
    if remote_ip.startswith(server_prefixes):
        return
    
    # Update database
    now = datetime.now()
    if peer_database[remote_ip]["first_seen"] is None:
        peer_database[remote_ip]["first_seen"] = now
        # Get geolocation asynchronously
        threading.Thread(target=lambda: update_geolocation(remote_ip), daemon=True).start()
    
    peer_database[remote_ip]["packets"] += 1
    peer_database[remote_ip]["last_seen"] = now
    
    if UDP in packet:
        peer_database[remote_ip]["ports"].add(packet[UDP].sport)
        peer_database[remote_ip]["ports"].add(packet[UDP].dport)
    
    # Try to extract Gamertag
    gamertag = extract_gamertag(packet)
    if gamertag and peer_database[remote_ip]["gamertag"] == "🔍 Scanning...":
        peer_database[remote_ip]["gamertag"] = gamertag
        print(f"\n{Fore.GREEN}🎮 {remote_ip} → {gamertag}{Style.RESET_ALL}")

def update_geolocation(ip):
    city, country, isp = get_ip_geolocation(ip)
    peer_database[ip]["city"] = city
    peer_database[ip]["country"] = country
    peer_database[ip]["isp"] = isp

# ========== LIVE DASHBOARD ==========
def live_dashboard():
    """Live-updating dashboard - refreshes every 3 seconds"""
    while not stop_sniffing.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"{Fore.GREEN}╔══════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.GREEN}║              🥔 POTATO ELITE - LIVE PLAYER TRACKER 🎮            ║{Style.RESET_ALL}")
        print(f"{Fore.GREEN}╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📡 Xbox IP: {xbox_ip if xbox_ip else 'Scanning...'} | MAC: {xbox_mac if xbox_mac else 'Unknown'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⏱ Last Updated: {datetime.now().strftime('%H:%M:%S')} | Players Found: {len(peer_database)}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        
        if not peer_database:
            print(f"{Fore.RED}⚠ No players detected yet.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Make sure:{Style.RESET_ALL}")
            print(f"   1. You're in an Xbox party with friends")
            print(f"   2. Your friends have their mics on")
            print(f"   3. You're in Fortnite Creative together")
        else:
            print(f"{Fore.WHITE}{'IP Address':<18} {'Gamertag':<20} {'Packets':<8} {'Location':<25} {'Last Seen'}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{'-'*85}{Style.RESET_ALL}")
            
            for ip, data in sorted(peer_database.items(), key=lambda x: x[1]['packets'], reverse=True):
                gamertag = data['gamertag'][:18] if data['gamertag'] != "🔍 Scanning..." else f"{Fore.YELLOW}🔍 Scanning...{Style.RESET_ALL}"
                location = f"{data['city']}, {data['country']}" if data['city'] != "Unknown" else "📍 Locating..."
                last_seen = data['last_seen'].strftime('%H:%M:%S') if data['last_seen'] else 'Never'
                print(f"{Fore.CYAN}{ip:<18}{Style.RESET_ALL} {gamertag:<20} {Fore.GREEN}{data['packets']:<8}{Style.RESET_ALL} {Fore.WHITE}{location:<25}{Style.RESET_ALL} {last_seen}")
        
        print(f"{Fore.MAGAZINE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[Q] Quit   [E] Export to JSON   [R] Refresh Now   [C] Clear Database{Style.RESET_ALL}")
        
        # Check for user input without blocking
        if sys.stdin in select_input():
            choice = sys.stdin.readline().strip().lower()
            if choice == 'q':
                stop_sniffing.set()
                break
            elif choice == 'e':
                export_to_json()
            elif choice == 'c':
                peer_database.clear()
                print(f"{Fore.GREEN}Database cleared!{Style.RESET_ALL}")
                time.sleep(1)
        
        time.sleep(3)

def select_input():
    """Non-blocking input check for Windows"""
    import msvcrt
    if msvcrt.kbhit():
        return [sys.stdin]
    return []

def export_to_json():
    filename = f"xbox_players_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    export_data = {}
    for ip, data in peer_database.items():
        export_data[ip] = {
            "gamertag": data["gamertag"],
            "packets": data["packets"],
            "first_seen": data["first_seen"].isoformat() if data["first_seen"] else None,
            "last_seen": data["last_seen"].isoformat() if data["last_seen"] else None,
            "ports": list(data["ports"]),
            "city": data["city"],
            "country": data["country"],
            "isp": data["isp"]
        }
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    print(f"{Fore.GREEN}✓ Exported to {filename}{Style.RESET_ALL}")

# ========== MAIN ==========
def main():
    print(f"{Fore.GREEN}╔══════════════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.GREEN}║     🥔 POTATO ULTIMATE - XBOX IP + GAMERTAG MAPPER    ║{Style.RESET_ALL}")
    print(f"{Fore.GREEN}║              ELITE EDITION - NO CONFIG NEEDED         ║{Style.RESET_ALL}")
    print(f"{Fore.GREEN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    
    # Auto-detect Xbox
    if not auto_detect_xbox():
        print(f"{Fore.RED}❌ Could not detect Xbox. Make sure it's on the same network as your PC.{Style.RESET_ALL}")
        input("Press Enter to exit...")
        return
    
    print(f"{Fore.CYAN}[2/5] Starting packet capture on all interfaces...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[3/5] Listening for Xbox traffic...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[4/5] Join an Xbox party with friends and speak!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[5/5] Dashboard loading in 3 seconds...{Style.RESET_ALL}")
    time.sleep(3)
    
    # Start sniffing thread
    sniff_thread = threading.Thread(
        target=lambda: sniff(
            prn=packet_callback,
            store=0,
            filter="udp",
            timeout=None,
            stop_filter=lambda x: stop_sniffing.is_set()
        ),
        daemon=True
    )
    sniff_thread.start()
    
    # Start dashboard
    live_dashboard()
    
    print(f"\n{Fore.GREEN}🎉 Session ended. Final data saved to memory.{Style.RESET_ALL}")
    export_to_json()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Goodbye, butter! Stay elite!{Style.RESET_ALL}")
        export_to_json()
