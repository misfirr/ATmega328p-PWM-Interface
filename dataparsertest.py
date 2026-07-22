import serial
import time

#setup
COM_PORT = 'COM4' 
BAUD_RATE = 9600

def run_telemetry_test():
    try:
        # Open the serial connection
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)

        while True:
            if ser.in_waiting > 0:
                raw_line = ser.readline().decode('utf-8').strip()

                if raw_line.startswith("T:"):
                    raw_data = raw_line[2:]  # Remove the "T:" prefix

                    #split into list
                    data = raw_data.split(',')

                    if len(data) == 6:
                        current_duty   = data[0]
                        target_duty    = data[1]
                        safety_limit   = data[2]
                        ramp_period    = data[3]
                        frequency      = data[4]
                        output_enabled = "ON" if data[5] == '1' else "OFF"

                    #print formatted data

                    print(f"--- TELEMETRY UPDATE ---")
                    print(f"Output State : {output_enabled}")
                    print(f"Duty Cycle   : {current_duty}% (Target: {target_duty}%)")
                    print(f"Safety Limit : {safety_limit}%")
                    print(f"Ramp Period  : {ramp_period} ms")
                    print(f"Frequency    : {frequency} Hz")
                    print("-" * 24)
                
                elif raw_line:
                    # 2. It is a standard message! (e.g. "System Ready.")
                    print(f"[BOARD MESSAGE] {raw_line}")
                    
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        print("Make sure the Arduino IDE Serial Monitor is closed!")
    except KeyboardInterrupt:
        print("\nExiting test. Closing port...")
        ser.close()

run_telemetry_test()