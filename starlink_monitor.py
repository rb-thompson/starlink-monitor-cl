#!/usr/bin/env python3
import subprocess
import argparse
import sys
import os
import time
from datetime import datetime
import colorama
from colorama import Style

# Initialize colorama for Windows compatibility
colorama.init()

# ANSI color codes
PURPLE = "\033[38;2;167;139;250m"
CYAN = "\033[38;2;34;211;238m"
MAGENTA = "\033[38;2;173;255;47m"
BLUE = "\033[38;2;0;183;235m"
RESET = Style.RESET_ALL

# Expected dashboard line count (4 sections × 2 lines + 1 header + 1 version + 1 footer)
DASHBOARD_LINES = 11

def fetch_starlink_data(mode="status"):
    """Fetch data from Starlink dish using starlink-grpc-tools."""
    try:
        python_exe = sys.executable
        result = subprocess.run(
            [python_exe, "dish_grpc_text.py", "-v", mode],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.getcwd(), "starlink-grpc-tools")
        )
        if result.stderr:
            log_error(f"Error fetching {mode} data: {result.stderr}")
            return {}
        
        # Log raw output for debugging
        # log_debug(f"Raw {mode} output:\n{result.stdout}")
        
        # Parse output, preserving all values
        lines = result.stdout.strip().split("\n")
        data = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().replace("_", " ").lower()
                value = value.strip()
                data[key] = value if value else "0"
        log_debug(f"Fetched {mode} data: {data}")
        log_debug(f"Available keys: {list(data.keys())}")
        return data
    except Exception as e:
        log_error(f"Failed to fetch {mode} data: {e}")
        return {}

def log_error(message):
    """Log errors to logs/errors.txt with timestamp."""
    os.makedirs("logs", exist_ok=True)
    with open("logs/errors.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {message}\n")

def log_debug(message):
    """Log debug info to logs/errors.txt."""
    os.makedirs("logs", exist_ok=True)
    with open("logs/errors.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DEBUG: {message}\n")

def log_dashboard(output):
    """Log rendered dashboard to logs/dashboard.txt with line numbers."""
    os.makedirs("logs", exist_ok=True)
    lines = output.split("\n")
    numbered_output = "\n".join(f"{i+1:2d}: {line}" for i, line in enumerate(lines))
    max_line_length = max(len(line.rstrip()) for line in lines)
    with open("logs/dashboard.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard (lines: {len(lines)}, max length: {max_line_length}):\n{numbered_output}\n{'-'*80}\n")
    log_debug(f"Rendered dashboard with {len(lines)} lines, max length {max_line_length}")

def format_uptime(seconds):
    """Convert uptime seconds to days, hours, minutes."""
    try:
        seconds = int(float(seconds))
        days = seconds // (24 * 3600)
        hours = (seconds % (24 * 3600)) // 3600
        minutes = (seconds % 3600) // 60
        return f"{days}d {hours:02d}h {minutes:02d}m"
    except:
        return "0d 00h 00m"

def ascii_progress_bar(value, max_value, width=20, fill_char="█", empty_char="─"):
    """Create an ASCII progress bar without brackets."""
    filled = int(value * width / max_value)
    bar = fill_char * filled + empty_char * (width - filled)
    return f"{CYAN}{bar}{RESET}"

def render_dashboard(status_data, ping_data, mode="status", debug=False):
    """Render compact dashboard with flush-left indicators."""
    # Map output keys to expected keys
    key_map = {
        "uptime": "uptimes",
        "snr": "snr",
        "signal to noise ratio": "snr",
        "pop ping latency ms": "pop ping latency ms",
        "downlink throughput bps": "downlink throughput bps",
        "pop ping drop rate": "count full ping drop",
        "count full ping drop": "count full ping drop",
        "count partial ping drop": "count partial ping drop",
        "hardware version": "hardware version",
        "software version": "software version",
        "gps sats": "gps sats",
        "is snr above noise floor": "is snr above noise floor"
    }
    normalized_data = {key_map.get(k, k): v for k, v in status_data.items()}
    normalized_data.update({key_map.get(k, k): v for k, v in ping_data.items()})

    # Extract metrics with defaults
    uptime = float(normalized_data.get("uptimes", 0))
    snr = normalized_data.get("snr", "N/A")
    latency = float(normalized_data.get("pop ping latency ms", 0))
    full_outages = int(float(normalized_data.get("count full ping drop", 0)))
    partial_outages = int(float(normalized_data.get("count partial ping drop", 0)))
    downlink = float(normalized_data.get("downlink throughput bps", 0)) / 1e6
    hardware_version = normalized_data.get("hardware version", "Unknown")
    software_version = normalized_data.get("software version", "Unknown")
    gps_sats = normalized_data.get("gps sats", "Unknown")
    is_snr_above_noise_floor = normalized_data.get("is snr above noise floor", "False").lower() == "true"

    # Log unmapped keys for debugging
    unmapped_keys = [k for k in status_data if k not in key_map]
    if unmapped_keys:
        log_debug(f"Unmapped keys in status_data: {unmapped_keys}")

    # Build dashboard
    output = []
    output.append(f"--- {BLUE}Starlink Diagnostics{RESET} ---")
    output.append(f"{PURPLE}HW:{RESET}{MAGENTA} {hardware_version}{RESET} {PURPLE}| SW:{RESET} {MAGENTA}{software_version}{RESET} {PURPLE}| SATS:{RESET}{MAGENTA} {gps_sats}{RESET}")
    output.append(f"{PURPLE}[ UPT ]{RESET} Online: {format_uptime(uptime)}")
    output.append(f"Status:  {ascii_progress_bar(uptime / (30 * 24 * 3600), 1.0, fill_char='█')}")
    output.append(f"{PURPLE}[ LAT ]{RESET} Latency: {latency:.1f} ms")
    output.append(f"Signal:  {ascii_progress_bar(latency / 100, 1.0, fill_char='▉')}")
    output.append(f"{PURPLE}[ TPT ]{RESET} Down: {downlink:.2f} Mbps")
    output.append(f"Stream:  {ascii_progress_bar(downlink / 200, 1.0, fill_char='▉')}")

    # Mode-specific section
    if mode == "ping_drop":
        total_outages = full_outages + partial_outages
        output.append(f"{PURPLE}[ OUT ]{RESET} Outages: {total_outages} ({full_outages} full, {partial_outages} partial)")
        output.append(f"Grid:    {ascii_progress_bar(total_outages / 10, 1.0, fill_char='▒')}")
    else:
        output.append(f"{PURPLE}[ SNR ]{RESET} Signal: {'N/A' if snr in ('N/A', '0') else snr}{' (Good)' if is_snr_above_noise_floor else ' (Weak)'}")
        output.append(f"Quality: {ascii_progress_bar(float(snr) / 10 if snr not in ('N/A', '0') else 0, 1.0, fill_char='─')}")

    output.append(f"{PURPLE}Press Ctrl+C to exit.{RESET}")

    # Ensure fixed line count
    output_str = "\n".join(output)
    lines = output_str.split("\n")
    if len(lines) < DASHBOARD_LINES:
        output_str += "\n" * (DASHBOARD_LINES - len(lines))
    elif len(lines) > DASHBOARD_LINES:
        output_str = "\n".join(lines[:DASHBOARD_LINES])

    return output_str

def main():
    parser = argparse.ArgumentParser(description="Starlink Terminal Dashboard")
    parser.add_argument("--mode", default="status", choices=["status", "ping_drop"],
                        help="Data mode: status or ping_drop")
    parser.add_argument("--debug", action="store_true", help="Log raw data to errors.txt")
    args = parser.parse_args()

    # Clear logs at start
    os.makedirs("logs", exist_ok=True)
    with open("logs/errors.txt", "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Starlink Monitor\n")
    with open("logs/dashboard.txt", "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Dashboard Log\n")

    # Clear screen once at start
    os.system('cls' if os.name == 'nt' else 'clear')

    # Debug mode: Print log prompt
    if args.debug:
        print(f"{PURPLE}Debug mode enabled. Raw data logged to logs/errors.txt.{RESET}")
        print(f"{PURPLE}Starting dashboard...{RESET}")
        time.sleep(1)  # Brief pause to show prompt
        os.system('cls' if os.name == 'nt' else 'clear')

    # Refresh loop
    try:
        first_run = True
        while True:
            status_data = fetch_starlink_data("status")
            ping_data = fetch_starlink_data("ping_drop") if args.mode == "ping_drop" else status_data
            log_debug(f"Status data: {status_data}")
            log_debug(f"Ping data: {ping_data}")

            # Render and print dashboard
            output = render_dashboard(status_data, ping_data, mode=args.mode, debug=args.debug)
            print(f"\033[H{output}", end="")
            sys.stdout.flush()
            log_dashboard(output)

            first_run = False
            time.sleep(1)
    except KeyboardInterrupt:
        log_debug("Monitor stopped by user")
        print(f"\n{PURPLE}[INFO] Transmission ended. Check logs/errors.txt and logs/dashboard.txt for details.{RESET}")
        sys.stdout.flush()
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        print(f"\n{PURPLE}[ERROR] Unexpected error: {e}. Check logs/errors.txt and logs/dashboard.txt.{RESET}")
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()