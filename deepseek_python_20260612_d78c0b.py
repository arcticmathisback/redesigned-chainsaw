#!/usr/bin/env python3
# ULTIMATE DIAGNOSTIC - Shows ALL UDP traffic from your Xbox
# Run as Administrator

import os
import sys
import subprocess
import time
from datetime import datetime

# Auto-install scapy
try:
    from scapy.all import sniff, IP, UDP, Ether
except ImportError:
    print("[*] Installing scapy...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scapy', '--quiet'])
    from scapy.all import sniff, IP, UDP, Ether

# Colors for Windows
os.system('color')
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
WHITE = '\033[97m'
RESET = '\033[0m'

print(f"{GREEN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
print(f"{GREEN}║           🥔 ULTIMATE DIAGNOSTIC - XBOX TRAFFIC SCANNER         ║{RESET}")
print(f"{GREEN}╚══════════════════════════════════════════════════════════════════╝{RESET}")

# Get Xbox IP from user
xbox_ip = input(f"{CYAN}📡 Enter your Xbox IP address (from Xbox Settings): {RESET}").strip()
print(f"{GREEN}✓ Target Xbox IP: {xbox_ip}{RESET}")

# Get PC's local IP
import socket
pc_ip = socket.gethostbyname(socket.gethostname())
print(f"{GREEN}✓ Your PC IP: {pc_ip}{RESET}")

# Try to get Xbox MAC
try:
    result = subprocess.run(f"arp -a {xbox_ip}", capture_output=True, text=True, shell=True)
    for line in result.stdout.split('\n'):
        if xbox_ip in line:
            parts = line.split()
            if len(parts) >= 2:
                xbox_mac = parts[1].upper()
                print(f"{GREEN}✓ Xbox MAC found: {xbox_mac}{RESET}")
                break
except:
    xbox_mac = None

print(f"\n{YELLOW}📡 SCANNING FOR 60 SECONDS...{RESET}")
print(f"{YELLOW}📢 ON YOUR XBOX, DO THIS NOW:{RESET}")
print(f"   1. Start an XBOX PARTY (not Fortnite game chat)")
print(f"   2. Invite at least 2 friends")
print(f"   3. Everyone turn MIC ON")
print(f"   4. Everyone SAY SOMETHING repeatedly")
print(f"   5. Also try joining a Fortnite Creative match")
print(f"\n{CYAN}Press Enter to start scanning...{RESET}")
input()

# Statistics
packets_found = 0
xbox_packets = 0
other_ips = set()
xbox_destinations = set()

def packet_callback(packet):
    global packets_found, xbox_packets
    
    packets_found += 1
    
    if Ether not in packet or IP not in packet or UDP not in packet:
        return
    
    src = packet[IP].src
    dst = packet[IP].dst
    
    # Check if packet involves Xbox
    if src == xbox_ip:
        xbox_packets += 1
        xbox_destinations.add(dst)
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Color based on destination type
        if dst.startswith(('192.168.', '10.', '172.')):
            color = CYAN
            ptype = "LOCAL"
        elif dst.startswith(('34.', '52.', '99.', '13.', '20.', '40.', '54.', '143.', '3.', '18.', '35.')):
            color = YELLOW
            ptype = "SERVER"
        else:
            color = GREEN
            ptype = "🎮 PLAYER!"
        
        print(f"{color}[{timestamp}] Xbox → {dst} [{ptype}] (UDP port {packet[UDP].dport}){RESET}")
        
    elif dst == xbox_ip:
        xbox_packets += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if src.startswith(('192.168.', '10.', '172.')):
            color = CYAN
            ptype = "LOCAL"
        elif src.startswith(('34.', '52.', '99.', '13.', '20.', '40.', '54.', '143.', '3.', '18.', '35.')):
            color = YELLOW
            ptype = "SERVER"
        else:
            color = GREEN
            ptype = "🎮 PLAYER!"
        
        print(f"{color}[{timestamp}] {src} → Xbox [{ptype}] (UDP port {packet[UDP].sport}){RESET}")
        
        if ptype == "🎮 PLAYER!":
            other_ips.add(src)
    else:
        return

# Start sniffing with timeout
print(f"\n{GREEN}🔍 SNIFFING FOR 60 SECONDS...{RESET}\n")

try:
    sniff(
        prn=packet_callback,
        store=0,
        filter="udp",
        timeout=60
    )
except Exception as e:
    print(f"{RED}Error: {e}{RESET}")

# Summary
print(f"\n{GREEN}{'='*60}{RESET}")
print(f"{GREEN}📊 DIAGNOSTIC SUMMARY{RESET}")
print(f"{GREEN}{'='*60}{RESET}")

print(f"{WHITE}Total UDP packets seen: {packets_found}{RESET}")
print(f"{GREEN}Packets from/to your Xbox: {xbox_packets}{RESET}")

if xbox_packets == 0:
    print(f"\n{RED}❌❌❌ CRITICAL: NO XBOX TRAFFIC DETECTED!{RESET}")
    print(f"\n{YELLOW}POSSIBLE REASONS:{RESET}")
    print(f"   1. Wrong Xbox IP — Double-check in Xbox Settings → Network → Advanced")
    print(f"   2. Xbox and PC on DIFFERENT networks (check router)")
    print(f"   3. Windows firewall blocking packet capture")
    print(f"   4. Npcap not installed or not in promiscuous mode")
    print(f"   5. Run this command to test connectivity:")
    print(f"      ping {xbox_ip}")
    
    # Try ping test
    print(f"\n{CYAN}Running ping test...{RESET}")
    result = subprocess.run(f"ping -n 2 {xbox_ip}", capture_output=True, text=True, shell=True)
    if "Reply from" in result.stdout:
        print(f"{GREEN}✓ Ping SUCCESS — Xbox is reachable!{RESET}")
        print(f"{YELLOW}  But no UDP packets seen. This means: Xbox is not sending/receiving UDP traffic{RESET}")
        print(f"  → Are you in an Xbox PARTY with mics ON?")
        print(f"  → Is your NAT type OPEN? (Xbox Settings → Network)")
    else:
        print(f"{RED}❌ Ping FAILED — Xbox not reachable!{RESET}")
        print(f"  → Check: same network? Both wired/Wi-Fi?")
        
elif xbox_packets > 0:
    print(f"\n{GREEN}✓ SUCCESS! Xbox traffic detected!{RESET}")
    print(f"\n{YELLOW}Destinations your Xbox talked to:{RESET}")
    for dest in list(xbox_destinations)[:10]:
        if dest.startswith(('34.', '52.', '99.', '13.', '20.', '40.')):
            print(f"  → {dest} (Epic/Microsoft server)")
        elif dest.startswith(('192.168.', '10.', '172.')):
            print(f"  → {dest} (Local network)")
        else:
            print(f"  → {GREEN}{dest} (POTENTIAL PLAYER IP!){RESET}")
    
    if other_ips:
        print(f"\n{GREEN}🎮 PLAYER IPs DETECTED:{RESET}")
        for ip in other_ips:
            print(f"  → {GREEN}{ip}{RESET}")
    else:
        print(f"\n{YELLOW}⚠ No player IPs detected — only server traffic.{RESET}")
        print(f"  → Make sure you're in an XBOX PARTY, not Fortnite game chat")
        print(f"  → Make sure friends have MICS ON and are SPEAKING")

print(f"\n{GREEN}{'='*60}{RESET}")
input("\nPress Enter to exit...")