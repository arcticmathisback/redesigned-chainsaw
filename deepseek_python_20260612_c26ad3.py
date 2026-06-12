#!/usr/bin/env python3
# Potato Diagnostic Tool - Checks if your PC is ready
# Run as Administrator
# NO REMOTE CONTROL - Just tells YOU what's missing

import os
import sys
import subprocess
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_npcap():
    try:
        result = subprocess.run(['sc', 'query', 'npcap'], capture_output=True, text=True, shell=True)
        if 'RUNNING' in result.stdout or 'STOPPED' in result.stdout:
            return True, "Installed"
        # Check Program Files
        if os.path.exists(r'C:\Program Files\Npcap'):
            return True, "Installed but service not running"
        return False, "Not found"
    except:
        return False, "Could not check"

def check_scapy():
    try:
        import scapy
        return True, f"Version {scapy.__version__}"
    except ImportError:
        return False, "Not installed"

def check_network_permissions():
    try:
        # Try to open raw socket
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        s.close()
        return True, "Raw sockets available"
    except PermissionError:
        return False, "Need Administrator privileges"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"

def main():
    print("="*60)
    print("🥔 POTATO DIAGNOSTIC TOOL")
    print("="*60)
    print("This tool ONLY checks your PC. No data is sent anywhere.")
    print("")
    
    # Check 1: Admin
    admin = is_admin()
    print(f"[1] Administrator Mode: {'✅ YES' if admin else '❌ NO - Run as Admin'}")
    
    # Check 2: Npcap
    npcap_installed, npcap_status = check_npcap()
    print(f"[2] Npcap Driver: {'✅ ' + npcap_status if npcap_installed else '❌ ' + npcap_status}")
    if not npcap_installed:
        print("    → Download from: https://npcap.com")
        print("    → Install with 'WinPcap API-compatible mode' checked")
    
    # Check 3: Scapy
    scapy_ok, scapy_status = check_scapy()
    print(f"[3] Scapy Library: {'✅ ' + scapy_status if scapy_ok else '❌ ' + scapy_status}")
    if not scapy_ok:
        print("    → Run: pip install scapy")
    
    # Check 4: Raw sockets
    raw_ok, raw_status = check_network_permissions()
    print(f"[4] Raw Socket Access: {'✅ ' + raw_status if raw_ok else '❌ ' + raw_status}")
    
    # Check 5: Network interface
    print(f"[5] Active Network Interfaces:")
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        for name, addrs in interfaces.items():
            for addr in addrs:
                if addr.family == 2:  # AF_INET
                    if addr.address != '127.0.0.1':
                        print(f"    → {name}: {addr.address}")
    except:
        print("    → Could not list (install psutil: pip install psutil)")
    
    # Summary
    print("")
    print("="*60)
    if admin and npcap_installed and scapy_ok and raw_ok:
        print("✅ YOUR PC IS READY! Run the main Potato script.")
    else:
        print("❌ YOUR PC NEEDS SETUP. Fix the missing items above.")
        print("")
        print("Quick fix commands (run as Admin in PowerShell):")
        print("  pip install scapy psutil colorama")
        print("  # Then install Npcap from https://npcap.com")
    print("="*60)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()