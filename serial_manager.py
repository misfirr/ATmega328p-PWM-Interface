#telemetry gathering & command issuing 

import serial
from PyQt6.QtCore import QObject, pyqtSignal

class SerialManager(QObject) :

    telemetry_updated = pyqtSignal(dict) # sends telmetry data to the gui
    message_received = pyqtSignal(str)     
    connection_changed = pyqtSignal(bool)


    def __init__(self):
        super().__init__()

        self.serial_port = None
        self.is_connected = False

    def connect_board(self, port_name, baud_rate=9600):
        #Attempts to open the serial port.
        try:
            self.serial_port = serial.Serial(port_name, baud_rate, timeout=0.1)
            self.is_connected = True

            # Broadcast the good news to the GUI
            self.connection_changed.emit(True)
            self.message_received.emit(f"Successfully connected to {port_name}.")         

        except serial.SerialException as e:
            self.is_connected = False
            self.connection_changed.emit(False)
            self.message_received.emit(f"Connection failed: {e}")

    def disconnect_board(self):
        """Safely closes the serial port."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            
        self.is_connected = False
        self.connection_changed.emit(False)
        self.message_received.emit("Disconnected from board.")

    def send_command(self, command_string):
        """Sends a formatted string to the Arduino."""
        # Only try to send if we actually have an open connection
        if self.is_connected and self.serial_port and self.serial_port.is_open:
            try:
                # Add the newline character your Arduino expects and convert to bytes
                full_command = f"{command_string}\n"
                self.serial_port.write(full_command.encode('utf-8'))
            except serial.SerialException as e:
                # If something goes wrong, we can broadcast the error to the GUI
                self.message_received.emit(f"Error sending command: {e}")

    def read_loop(self):
        """This runs continuously in a background thread."""
        while self.is_connected:
            try:
                # Try to read incoming telemetry
                if self.serial_port and self.serial_port.in_waiting > 0:
                    raw_line = self.serial_port.readline().decode('utf-8').rstrip('\r\n')
                    # (Telemetry parsing logic goes here)
                    if raw_line.startswith("T:"):
                        raw_data = raw_line.strip()[2:]  # Remove the "T:" prefix

                        #split into list
                        data = raw_data.split(',')

                        if len(data) == 6:
                                # Build a clean, local dictionary
                                payload = {
                                    "current_duty": int(data[0]),
                                    "target_duty": int(data[1]),
                                    "safety_limit": int(data[2]),
                                    "ramp_period": int(data[3]),
                                    "frequency": int(data[4]),
                                    "output_enabled": True if data[5] == '1' else False
                                }
                                
                                # Emit the dictionary to the GUI's radio tower
                                self.telemetry_updated.emit(payload)
                                print(payload) # For debugging purposes <3
                    
                    elif raw_line:
                        # 2. It is a standard message! (e.g. "System Ready.")
                        # Emit the text string to the GUI's radio tower
                        self.message_received.emit(raw_line)
                    
                    
            except serial.SerialException as e:
                # C
                # The read failed, so we trigger our disconnect protocol.
                self.disconnect_board() # This function emits connection_changed(False)
                self.message_received.emit("Hardware disconnected unexpectedly.")
                break # Kill the background loop