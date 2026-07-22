import serial
import time

# 1. Configuration
arduino_port = "COM4"  # <--- CHANGE THIS TO YOUR ACTUAL PORT
baud_rate = 9600

print(f"Attempting to connect to {arduino_port}...")

try:
    # 2. Open the Serial Connection
    # timeout=1 means it will wait up to 1 second for data before moving on
    board = serial.Serial(arduino_port, baud_rate, timeout=1)
    
    # CRITICAL: Opening a serial port forces the Arduino to restart. 
    # We must wait ~2 seconds for the bootloader to finish before sending data.
    print("Port open! Waiting 2 seconds for Arduino to boot...")
    time.sleep(2) 
    
    # 3. Read the initial startup messages from the Arduino
    print("\n--- Startup Messages ---")
    while board.in_waiting > 0:
        startup_msg = board.readline().decode('utf-8').strip()
        print(f"Arduino: {startup_msg}")

    # 4. Send a command to the Arduino
    target_duty = "15\n" # We want it to ramp up to 15%
    print(f"\n--- Sending Target Duty: {target_duty.strip()}% ---")
    
    # We must encode the python string into raw bytes for the serial cable
    board.write(target_duty.encode('utf-8'))

    # 5. Listen to the telemetry for a few seconds to watch it ramp up
    print("\n--- Listening to Telemetry ---")
    for _ in range(15): # Loop 15 times (with a 0.5s pause = 7.5 seconds of listening)
        if board.in_waiting > 0:
            # Read the raw bytes, decode back to string, and strip invisible characters
            telemetry = board.readline().decode('utf-8').strip()
            if telemetry:
                print(f"Arduino: {telemetry}")
        
        time.sleep(0.5)

    # 6. Safely close the connection
    board.close()
    print("\nTest complete. Port safely closed.")

except serial.SerialException as e:
    print(f"\n[ERROR] Could not connect to {arduino_port}.")
    print(f"Details: {e}")
    print("Make sure the Serial Monitor in the Arduino IDE is CLOSED!")