from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QComboBox, QPushButton, QLineEdit)
from PyQt6.QtSerialPort import QSerialPortInfo
from PyQt6.QtCore import Qt,QTimer






class BoardStatusWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 1. The Outer Wrapper
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 2. The Visible Card
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame {
                border: 2px solid #555555;
                border-radius: 20px;
                background-color: #2b2b2b;
            }
            QLabel { 
                border: none; 
                background-color: transparent; 
            }
        """)

        # 3. The Inner Layout
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15) # Adds a nice 15px vertical gap between elements

        # --- TITLE ---
        title = QLabel("<b>BOARD INFO & STATUS</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the title
        card_layout.addWidget(title)
        
        # --- PORT SELECTION ROW ---
        card_layout.addWidget(QLabel("Select COM Port:"))
        
        # We create a horizontal layout specifically for this row
        port_row_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.btn_refresh = QPushButton("Refresh")
        
        # Add the combo and button to the horizontal row (Combo takes 2/3 space, Button takes 1/3)
        port_row_layout.addWidget(self.port_combo, stretch=2)
        port_row_layout.addWidget(self.btn_refresh, stretch=1)
        
        # Add the horizontal row into our main vertical card
        card_layout.addLayout(port_row_layout)

        # --- BAUD RATE ---
        card_layout.addWidget(QLabel("Baud Rate: <b>9600</b>"))

        # --- CONNECT BUTTON ---
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setMinimumHeight(40) # Make it a large, easily clickable button
        self.btn_connect.setCheckable(True)   # Allows the button to act as a toggle (On/Off)
        card_layout.addWidget(self.btn_connect)

        # --- STATUS INDICATOR ---
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #ff5555; font-weight: bold;") # Red text
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        # --- ADD SOME SPACING ---
        card_layout.addSpacing(15) # Creates a visual gap before the settings

        # --- FREQUENCY CONTROL ROW ---
        freq_row_layout = QHBoxLayout()
        
        self.freq_label = QLabel("Freq:")
        self.freq_label.setStyleSheet("font-weight: bold;")
        
        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText("e.g. 1000 or 1k") # Hint text inside the box
        
        self.btn_set_freq = QPushButton("Set")
        
        # Add them to the horizontal row
        freq_row_layout.addWidget(self.freq_label)
        freq_row_layout.addWidget(self.freq_input)
        freq_row_layout.addWidget(self.btn_set_freq)
        
        # Add the completed row to the main card layout
        card_layout.addLayout(freq_row_layout)

        # --- SETTINGS PLACEHOLDERS (The Red Dots) ---
        # We will turn these into real controls later!
        # self.limit_label = QLabel(" Safety Limit: ---")
        # self.ramp_label = QLabel(" Ramp Period: ---")
        # self.output_label = QLabel(" Output: ---")
        
        # card_layout.addWidget(self.limit_label)
        # card_layout.addWidget(self.ramp_label)
        # card_layout.addWidget(self.output_label)

        # --- SAFETY LIMIT ROW ---
        limit_row_layout = QHBoxLayout() 
        self.limit_label = QLabel(" Limit: ---")
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("e.g. 50")

        self.btn_set_limit = QPushButton("Set")
        
        limit_row_layout.addWidget(self.limit_label)
        limit_row_layout.addWidget(self.limit_input)
        limit_row_layout.addWidget(self.btn_set_limit)
        card_layout.addLayout(limit_row_layout)

        # --- RAMP PERIOD ROW ---
        ramp_row_layout = QHBoxLayout()
        self.ramp_label = QLabel(" Ramp: --- (ms)")
        self.ramp_input = QLineEdit()
        self.ramp_input.setPlaceholderText("e.g. 1000 (ms)")
        self.btn_set_ramp = QPushButton("Set")
        
        ramp_row_layout.addWidget(self.ramp_label)
        ramp_row_layout.addWidget(self.ramp_input)
        ramp_row_layout.addWidget(self.btn_set_ramp)
        card_layout.addLayout(ramp_row_layout)

        # --- OUTPUT CONTROL ROW ---

        output_row_layout = QHBoxLayout()
        #self.output_label = QLabel(" Output: ---") Deprecated now the indicator is the button itself
        
        self.btn_toggle_output = QPushButton("Output : ---")
        #it would be better to have a toggle button but for now we will use a normal 
        # button that changes its text and color based on the state of the output
        #BUT
        # If we set the button to be a built-in toggle (setCheckable(True)), the button relies purely on the user's mouse 
        # click to change its state 
        # The exact millisecond you click it, the UI assumes it worked and permanently presses the button down.
        # We get no feedback about the state of the board 
        """FEAR THE DESYNCING OF THE BUTTON oooo 👻"""

        self.btn_toggle_output.setMinimumHeight(40)
        
        #output_row_layout.addWidget(self.output_label)
        output_row_layout.addWidget(self.btn_toggle_output)
        card_layout.addLayout(output_row_layout)


        card_layout.addStretch() # Push everything up to the top

        # --- THE WATCHDOG TIMER --- calls clear_telemetry() every second if no new data arrives
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(1000) # 1000 milliseconds = 1 second
        self.telemetry_timer.timeout.connect(self.clear_telemetry)

        # 4. Assembly
        self.card.setLayout(card_layout)
        main_layout.addWidget(self.card)
        self.setLayout(main_layout)

        # 5. Initialization and Signals
        self.refresh_ports() # Auto-populate the drop-down on startup
        self.btn_refresh.clicked.connect(self.refresh_ports) # Wire up the refresh button

    # --- Widget Functions ---
    def refresh_ports(self):
        self.port_combo.clear() # Empty the current list
        
        # Ask Qt to scan the computer's USB/Serial ports
        for port in QSerialPortInfo.availablePorts():
            port_name = port.portName()      # e.g. "COM4"
            description = port.description() # e.g. "Arduino Uno" or "USB Serial Device"
            
            # Create a nice label for the user to read
            display_text = f"{port_name} - {description}"
            
            # Add it to the drop-down. 
            # 'userData' secretly stores the raw "COM3" string so we can pass it to the backend later!
            self.port_combo.addItem(display_text, userData=port_name)
            
        # Fallback if the Arduino isn't plugged in
        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found")

    def update_connection_ui(self, is_connected):
        """Updates the button, labels, and combo box based on connection state."""
        if is_connected:
            # Visuals for ACTIVE connection
            self.btn_connect.setText("Disconnect")
            self.btn_connect.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold;")
            
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: #55ff55; font-weight: bold;") # Green text
            
            # Lock the drop-down and refresh button so user can't change ports while connected
            self.port_combo.setEnabled(False)
            self.btn_refresh.setEnabled(False)
        else:
            # Visuals for DISCONNECTED state
            self.btn_connect.setText("Connect")
            self.btn_connect.setStyleSheet("") # Clearing this resets it to your default dark theme
            
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: #ff5555; font-weight: bold;") # Red text
            
            # Unlock the drop-down and refresh button
            self.port_combo.setEnabled(True)
            self.btn_refresh.setEnabled(True)
            
            # Ensure the button physically un-toggles itself
            self.btn_connect.setChecked(False)
    
    def update_telemetry(self, payload):
        """Updates the UI labels with live data from the data dictionary."""
        
        # 1. Start/Reset the 1-second countdown timer
        self.telemetry_timer.start()

        # 1. Update the Frequency label
        # We extract the 'frequency' value from the dictionary and update the text
        live_freq = payload["frequency"]
        self.freq_label.setText(f"Freq: {live_freq:,} Hz:")
        
        # 2. Update the placeholder dots while we're at it!
        live_limit = payload["safety_limit"]
        self.limit_label.setText(f" Safety Limit: {live_limit}%")
        
        live_ramp = payload["ramp_period"]
        self.ramp_label.setText(f" Ramp : {live_ramp} ms")
        
        # Format the boolean True/False into ON/OFF for readability

        """deprecated ,now the indicator is the button itself"""
        #out_state = "ON" if payload["output_enabled"] else "OFF"
        #self.output_label.setText(f" Output: {out_state}")     
        #self.btn_toggle_output.setText(f"Output : {out_state}") 

        if payload["output_enabled"]:
            self.btn_toggle_output.setText("Output : ON")
            # Apply the blue background, white text, and bold font
            self.btn_toggle_output.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold;")
        else:
            self.btn_toggle_output.setText("Output : OFF")
            # Clear the stylesheet to return it to the default dark theme
            self.btn_toggle_output.setStyleSheet("")


    
    def clear_telemetry(self):
        """Wipes the labels if data stops coming in (or if disconnected)."""

        print("[DEBUG] Watchdog Triggered! Wiping UI.")
        
        self.freq_label.setText("Freq: --- Hz:")
        self.limit_label.setText(" Limit: --- %")
        self.ramp_label.setText(" Ramp: --- ms")
        #self.output_label.setText(" Output: ---")
        self.btn_toggle_output.setText("Output : ---")
        self.btn_toggle_output.setStyleSheet("")
        self.telemetry_timer.stop() # Stop the timer until new data arrives