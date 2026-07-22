import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout , QLabel
from darktheme.widget_template_pyqt6 import DarkPalette


# import modules from the other files
from board_status import BoardStatusWidget
from duty_cycle import DutyCycleWidget
from serial_monitor import SerialMonitorWidget
#import serial manager and threading for background serial reading
from serial_manager import SerialManager
import threading    

logo = "██ ███████ ███████ ███████ \n██ ██      ██      ██      \n██ █████   █████   █████   \n██ ██      ██      ██      \n██ ███████ ███████ ███████"
                           
                           
# ██ ███████ ███████ ███████ 
# ██ ██      ██      ██      
# ██ █████   █████   █████   
# ██ ██      ██      ██      
# ██ ███████ ███████ ███████ 
        
                           
"""MAXIMUM VALEUS DO NOT CHANGE MOTHERFUCKER"""
NAME = "P-W-M Controller"
INFO = "IEEE SB UPATRAS - PES Chapter: Interface for arduino PWM experimentation v0.1"
MAX_FREQ = 100* 1000  # 100KHz
MAX_LIMIT = 60      # 60% duty cycle

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(NAME)
        self.resize(1000, 700)
        

        # 1. Create the central widget and master layout
        central_widget = QWidget()#central widget is the main container for the window's content ,
                                  #the window it self can't be layed out directly, so we create a central widget to hold all other widgets and layouts.

        mastermaster_layout = QVBoxLayout() #master of the master just so i can put a footer what the fuck am i doing

        master_layout = QHBoxLayout() # Horizontal layout (Left to Right)
                                      #any widget added to it will be automatically placed side-by-side, reading left to right.

        self.board = SerialManager() # Instantiate the manager


        # 2. Instantiate our custom panels
        self.left_panel = BoardStatusWidget()
        self.top_right_panel = DutyCycleWidget()
        self.bottom_right_panel = SerialMonitorWidget()
        #Output state variable to keep track of the current output state (ON/OFF)
        self.current_output_state = False

        # 3. Create a vertical layout specifically for the right side
        right_side_layout = QVBoxLayout()
        right_side_layout.addWidget(self.top_right_panel,stretch=1) # Takes 1 part of the height
        right_side_layout.addWidget(self.bottom_right_panel,stretch=2) # Takes 1 part of the height

        # 4. Add the left panel and the right layout to the master layout
        master_layout.addWidget(self.left_panel, stretch=1)      # Takes 1 part of the width
        master_layout.addLayout(right_side_layout, stretch=2)    # Takes 2 parts of the width

        #Add the master layout to the master master layout
        mastermaster_layout.addLayout(master_layout)
        # Apply the mastermaster layout
        central_widget.setLayout(mastermaster_layout)
        self.setCentralWidget(central_widget)

        """Footer"""

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(10, 0, 10, 5) # Tight margins
        
        version_label = QLabel(INFO)
        version_label.setStyleSheet("color: #666666; font-size: 10px;")
        
        self.global_status_label = QLabel("🔴 Offline")
        self.global_status_label.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")
        
        footer_layout.addWidget(version_label)
        footer_layout.addStretch() # Pushes the status to the far right
        footer_layout.addWidget(self.global_status_label)
        
        # Add everything to the absolute main layout
        mastermaster_layout.addLayout(footer_layout) 

        """Wiring Footer Status"""

        self.board.connection_changed.connect(self.update_global_status)

        """Wiring Board Status"""

        # Wire the connect button click to our toggle function
        self.left_panel.btn_connect.clicked.connect(self.toggle_connection)
        
        # Wire the backend connection status directly to the left panel's UI updater
        self.board.connection_changed.connect(self.left_panel.update_connection_ui)

        #Connect freq button to the send_frequency function
        self.left_panel.btn_set_freq.clicked.connect(self.send_frequency)

        # Wire the telemetry dictionary signal directly to the left panel's new function
        self.board.telemetry_updated.connect(self.left_panel.update_telemetry)

        # Wire the telemetry dictionary signal to the sync_board_state function
        self.board.telemetry_updated.connect(self.sync_board_state)

        # Wire the limit button to the send_limit function
        self.left_panel.btn_set_limit.clicked.connect(self.send_limit)
        #the function than triggers and pulls the input from the limit input field and sends it to the board   

        # Wire the ramp button to the send_ramp function
        self.left_panel.btn_set_ramp.clicked.connect(self.send_ramp)

        #Wire the enter key press in the input fields to the corresponding send functions
        self.left_panel.freq_input.returnPressed.connect(self.send_frequency)
        self.left_panel.limit_input.returnPressed.connect(self.send_limit)
        self.left_panel.ramp_input.returnPressed.connect(self.send_ramp)

        # Wire the output toggle button to the toggle_output function
        self.left_panel.btn_toggle_output.clicked.connect(self.toggle_output)   

        """Wiring Serial Monitor"""

        #wire send button to the send_raw_command function
        self.bottom_right_panel.btn_send.clicked.connect(self.send_raw_command)

        #wire the enter key press in the input box to the send_raw_command function
        self.bottom_right_panel.input_box.returnPressed.connect(self.send_raw_command)

        #wire incoming messages from the backend to the serial monitor's append_message function
        self.board.message_received.connect(self.bottom_right_panel.append_message)

        #wire the connection status to the serial monitor's UI updater for locking inputs
        self.board.connection_changed.connect(self.bottom_right_panel.update_connection_ui)

        """Wiring Duty Cycle Panel"""
        
        # Wire telemetry to the new Duty Cycle panel
        self.board.telemetry_updated.connect(self.top_right_panel.update_telemetry)
        
        # Wire the slider release event to our sender function
        self.top_right_panel.slider.sliderReleased.connect(self.send_duty)




    """Toggle Connection log for the Connect button"""
    def toggle_connection(self):
        """Triggered when the user clicks the Connect button on the board status panel."""
        if not self.board.is_connected:
            # Read the selected port directly from the combo box!
            selected_port = self.left_panel.port_combo.currentData()
            
            # Safety check: Don't try to connect if no real ports exist
            if selected_port == "No ports found":
                self.left_panel.btn_connect.setChecked(False) # Un-press the button
                return
                
            # Tell the backend to connect
            self.board.connect_board(selected_port)
            
            # If successful, launch the background reading loop
            if self.board.is_connected:
                threading.Thread(target=self.board.read_loop, daemon=True).start() 
                #daemon=True means the thread will automatically close when the main program exits
        else:
            # Tell the backend to disconnect
            self.board.disconnect_board()

    def send_frequency(self):

        """Parses the user's input, applies limits, and sends the command."""
        # 1. Grab the raw text and convert it to lowercase (so 'K' or 'k' both work)
        raw_text = self.left_panel.freq_input.text().strip().lower()

        multiplier = 1
        if raw_text.endswith('k'):
            multiplier = 1000
            raw_text = raw_text[:-1]  # Remove the 'k' from the string
        
        try:
            # Convert to an integer
            freq_value = int((float(raw_text) * multiplier))

            if freq_value > MAX_FREQ:
                freq_value = MAX_FREQ

            self.board.send_command(f"F:{freq_value}") # send constrained frequency to the backend
        
            self.left_panel.freq_input.clear()  # Clear the input field after sending

        except ValueError:
            # If the user entered something that isn't a number, we can ignore it or show an error
            self.left_panel.freq_input.setText("Invalid input")

    def send_limit(self):
        raw_text = self.left_panel.limit_input.text().strip()
        if not raw_text: return
        try:
            limit_val = int(raw_text)
            # Enforce 0-100% bounds
            if limit_val > MAX_LIMIT: limit_val = MAX_LIMIT
            if limit_val < 0: limit_val = 0
            
            self.board.send_command(f"L:{limit_val}") # Change 'L:' if needed
            self.left_panel.limit_input.clear()
        except ValueError:
            self.left_panel.limit_input.clear()

    def send_ramp(self):


        print("[DEBUG] Ramp button clicked.")
        raw_text = self.left_panel.ramp_input.text().strip()
        print(f"[DEBUG] Raw ramp input: '{raw_text}'")
        if not raw_text: return

        if raw_text.endswith('s'):
            raw_text = raw_text[:-1]  # Remove the 's' from the string
            
            try:
                ramp_val = int(raw_text)*1000  # Convert seconds to milliseconds
                print(f"[DEBUG] Parsed ramp value: {ramp_val}")
                self.board.send_command(f"P:{ramp_val}") 
                self.left_panel.ramp_input.clear()
            except ValueError:
                self.left_panel.ramp_input.clear()
                print(f"[DEBUG] error:{ValueError}")
        else:

            try:
                ramp_val = int(raw_text)
                print(f"[DEBUG] Parsed ramp value: {ramp_val}")
                self.board.send_command(f"P:{ramp_val}") 
                self.left_panel.ramp_input.clear()
            except ValueError:
                self.left_panel.ramp_input.clear()
                print(f"[DEBUG] error:{ValueError}")

    def send_duty(self):
            """Reads the slider and sends the target duty cycle."""
            target_val = self.top_right_panel.slider.value()
            self.board.send_command(f"D:{target_val}")
            
            # Optional: Echo it to the serial monitor so you can see it happen
            self.bottom_right_panel.append_sent_message(f"D:{target_val}")

    def toggle_output(self):
        """Checks the memorized state and sends the opposite command explicitly."""
        if self.current_output_state is True:
            # The board is currently ON, so we explicitly command it to turn OFF
            self.board.send_command("O:0")
            print("[DEBUG] Sent Command: 0:0 (Turn OFF)")
        else:
            # The board is currently OFF, so we explicitly command it to turn ON
            self.board.send_command("O:1")
            print("[DEBUG] Sent Command: 0:1 (Turn ON)")
    
    def sync_board_state(self, payload):
        """Silently memorizes the current output state every time telemetry arrives."""
        self.current_output_state = payload["output_enabled"]

    def send_raw_command(self):
            """Pulls text from the serial monitor input, sends it, and echoes it to the screen."""
            raw_text = self.bottom_right_panel.input_box.text().strip()
            
            if raw_text:
                # 1. Send it down the serial cable to the Arduino
                self.board.send_command(raw_text)
                
                # 2. Tell the monitor widget to display it locally in blue with ">>>"
                self.bottom_right_panel.append_sent_message(raw_text)
                
                # 3. Clear the input box
                self.bottom_right_panel.input_box.clear()
            
    def update_global_status(self, is_connected):
            """Catches the connection boolean and updates the footer text/color."""
            if is_connected:
                # Change text to Online and color to a bright terminal green
                self.global_status_label.setText("🟢 Online")
                self.global_status_label.setStyleSheet("color: #55ff55; font-size: 10px; font-weight: bold;")
            else:
                # Revert text to Offline and color to red
                self.global_status_label.setText("🔴 Offline")
                self.global_status_label.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")

#were done telos kalo ola kala

if __name__ == "__main__":


    print(logo)
    app = QApplication(sys.argv)
   
    # Apply the dark theme palette
    app.setPalette(DarkPalette())
    window = MainApp()
    window.show()
    sys.exit(app.exec())