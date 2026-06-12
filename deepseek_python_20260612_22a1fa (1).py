#!/usr/bin/env python3
# Xbox Live Party IP → Gamertag Mapper
# Run as Administrator on Windows 11
# Captures both IP and Gamertag from Xbox party chat packets

import socket
import struct
import re
import threading
import time
from datetime import datetime
from collections import defaultdict

try:
    from scapy.all import sniff, IP, UDP, Ether, Raw
    from scapy.arch.windows import get_windows_if_list
except ImportError:
    print("[!] Install scapy: pip install scapy")
    exit(1)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = CYAN = YELLOW = RED = MAGENTA = WHITE = ''
    Style.RESET_ALL = ''

# ========== CONFIGURATION ==========
XBOX_MAC = input("[?] Enter your Xbox Series S MAC address: ").strip().upper()
INTERFACE = None
# ===================================

# Storage: IP -> {gamertag, packets, first_seen, last_seen}
peer_database = defaultdict(lambda: {
    "gamertag": "Unknown",
    "packets": 0,
    "first_seen": None,
    "last_seen": None,
    "ports": set()
})

# Known Epic / Microsoft server IPs to ignore (not players)
IGNORE_IPS = {
    "34.120", "52.45", "99.82", "13.107", "20.50", "40.90",
    "52.113", "54.192", "143.204", "3.208", "18.164"
}

def extract_gamertag_from_packet(packet):
    """
    Attempt to extract Xbox Gamertag from UDP packet payload.
    Xbox Live sends Gamertag strings in plaintext or UTF-16LE format.
    """
    if Raw not in packet:
        return None
    
    raw_data = bytes(packet[Raw].load)
    
    # Try UTF-16LE decoding (Xbox uses this for Gamertags)
    try:
        decoded = raw_data.decode('utf-16le', errors='ignore')
        # Look for Gamertag pattern: usually between 3-15 chars, alphanumeric + spaces
        matches = re.findall(r'([A-Za-z0-9\s]{3,15})', decoded)
        for match in matches:
            match = match.strip()
            # Filter out common non-gamertag strings
            if len(match) >= 3 and match not in ["Xbox", "Live", "Microsoft", "Teredo", "STUN"]:
                if not match.isdigit():  # Gamertags aren't purely numbers
                    return match
    except:
        pass
    
    # Try UTF-8 as fallback
    try:
        decoded = raw_data.decode('utf-8', errors='ignore')
        matches = re.findall(r'([A-Za-z0-9\s]{3,15})', decoded)
        for match in matches:
            match = match.strip()
            if len(match) >= 3 and match not in ["Xbox", "Live", "Microsoft"]:
                if not match.isdigit():
                    return match
    except:
        pass
    
    return None

def is_player_ip(ip):
    """Check if IP belongs to a real player (not Epic/Microsoft servers)"""
    for prefix in IGNORE_IPS:
        if ip.startswith(prefix):
            return False
    
    # Local IPs are not players
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return False
    
    # Multicast / broadcast
    if ip.startswith("224.") or ip.startswith("239.") or ip == "0.0.0.0":
        return False
    
    return True

def packet_callback(packet):
    if Ether not in packet or packet[Ether].src.lower() != XBOX_MAC.lower():
        return
    
    if IP not in packet or UDP not in packet:
        return
    
    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    local_ip = socket.gethostbyname(socket.gethostname())
    
    # Determine remote IP (the other player)
    if src_ip != local_ip:
        remote_ip = src_ip
    else:
        remote_ip = dst_ip
    
    if not is_player_ip(remote_ip):
        return
    
    # Update database
    now = datetime.now()
    if peer_database[remote_ip]["first_seen"] is None:
        peer_database[remote_ip]["first_seen"] = now
        print(f"\n{Fore.GREEN}[NEW PLAYER] IP: {remote_ip}{Style.RESET_ALL}")
    
    peer_database[remote_ip]["packets"] += 1
    peer_database[remote_ip]["last_seen"] = now
    
    # Try to extract Gamertag
    gamertag = extract_gamertag_from_packet(packet)
    if gamertag and peer_database[remote_ip]["gamertag"] == "Unknown":
        peer_database[remote_ip]["gamertag"] = gamertag
        print(f"{Fore.CYAN}[✓ MAPPED] {remote_ip} → {gamertag}{Style.RESET_ALL}")

def interactive_lookup():
    """Allow butter to query IP -> Gamertag in real time"""
    while True:
        time.sleep(0.5)
        if not peer_database:
            continue
        
        print(f"\n{Fore.YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"{Fore.WHITE}ACTIVE PLAYERS IN YOUR PARTY / CREATIVE:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        
        for ip, data in peer_database.items():
            gamertag_display = f"{Fore.GREEN}{data['gamertag']}{Style.RESET_ALL}" if data['gamertag'] != "Unknown" else f"{Fore.RED}Unknown{Style.RESET_ALL}"
            print(f"  IP: {Fore.CYAN}{ip}{Style.RESET_ALL} → {gamertag_display}")
            print(f"     Packets: {data['packets']} | Last seen: {data['last_seen'].strftime('%H:%M:%S') if data['last_seen'] else 'Never'}")
        
        print(f"{Fore.YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}[?] Type 'lookup <IP>' to search, or 'refresh' to update, or Ctrl+C to stop{Style.RESET_ALL}")
        
        user_input = input("> ").strip().lower()
        if user_input.startswith("lookup"):
            _, ip_query = user_input.split(" ", 1)
            if ip_query in peer_database:
                print(f"{Fore.GREEN}{ip_query} → {peer_database[ip_query]['gamertag']}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}IP not found{Style.RESET_ALL}")
        elif user_input == "refresh":
            continue
        elif user_input == "exit":
            break

def main():
    print(f"{Fore.GREEN}╔══════════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.GREEN}║  Xbox Party IP → Gamertag Mapper v2.0            ║{Style.RESET_ALL}")
    print(f"{Fore.GREEN}║  Potato Elite Edition                            ║{Style.RESET_ALL}")
    print(f"{Fore.GREEN}╚══════════════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"[*] Target Xbox MAC: {XBOX_MAC}")
    print(f"[*] Sniffing UDP traffic... Press Ctrl+C to stop sniffing and enter lookup mode\n")
    
    try:
        # Start sniffing in a separate thread
        sniff_thread = threading.Thread(
            target=lambda: sniff(
                iface=INTERFACE,
                prn=packet_callback,
                store=0,
                filter="udp",
                timeout=None
            ),
            daemon=True
        )
        sniff_thread.start()
        
        # Give it 10 seconds to collect data
        print(f"{Fore.YELLOW}[*] Collecting packets for 10 seconds...{Style.RESET_ALL}")
        time.sleep(10)
        
        # Enter interactive lookup
        interactive_lookup()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Stopping...{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}Final IP → Gamertag Mapping:{Style.RESET_ALL}")
        for ip, data in peer_database.items():
            print(f"  {ip} → {data['gamertag']} ({data['packets']} packets)")

if __name__ == "__main__":
    main()