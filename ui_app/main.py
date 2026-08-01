import sys , os 
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon ,QAction 
from PyQt6.QtWidgets import QApplication, QMainWindow, QProgressBar, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QFileDialog, QStyle 
from darktheme.widget_template_pyqt6 import DarkPalette


# import modules from the other files
from board_status import BoardStatusWidget
from duty_cycle import DutyCycleWidget
from serial_monitor import SerialMonitorWidget
from script_manager import ScriptManager , ScriptRunner


#import serial manager and threading for background serial reading
from serial_manager import SerialManager
import threading    

logo = "██ ███████ ███████ ███████ \n██ ██      ██      ██      \n██ █████   █████   █████   \n██ ██      ██      ██      \n██ ███████ ███████ ███████"
                           
                           
# ██ ███████ ███████ ███████ 
# ██ ██      ██      ██      
# ██ █████   █████   █████   
# ██ ██      ██      ██      
# ██ ███████ ███████ ███████ 

if sys.platform == "win32":
    import ctypes
    
    id = 'ieeesbupatras.pwm_controller.1_5a' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(id)

                           
"DEFAULT VALUES DO NOT CHANGE MOTHERFUCKER"

DEBUG_MODE = True
NAME = "P-W-M Controller"
INFO = "IEEE SB UPATRAS - PES Chapter: Interface for microcontroller PWM experimentation v0.1.5a 1/8/26"
#Added scripting functionality (hopefully)
MAX_FREQ = 200* 1000  # 100KHz
MAX_LIMIT = 90      # 0% - 90%
LOGO_ON = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()

        
        self.script_defaults = { }
        self.script_commands = { }

        self.setWindowTitle(NAME)
        self.resize(1000, 700)

        icon_path = os.path.join(BASE_DIR, "icons", "blue.svg")
        logo_path = os.path.join(BASE_DIR, "icons", "blue.svg")

        self.setWindowIcon(QIcon(icon_path))

        # 1. Create the central widget and master layout
        central_widget = QWidget()#central widget is the main container for the window's content ,
                                  #the window it self can't be layed out directly, so we create a central widget to hold all other widgets and layouts.

        self.mastermaster_layout = QVBoxLayout() #master of the master just so i can put a footer what the fuck am i doing

        master_layout = QHBoxLayout() # Horizontal layout (Left to Right)
                                      #any widget added to it will be automatically placed side-by-side, reading left to right.

        self.board = SerialManager(debug=False) # Instantiate the manager

        self.latest_telemetry = { } #used to store the latest telemetry data for the script runner to access


        # Instantiate our custom panels
        self.left_panel = BoardStatusWidget(logo_path,LOGO_ON)
        self.top_right_panel = DutyCycleWidget()
        self.top_right_panel.setFixedHeight(200)  # Set a fixed height for the top right panel
        self.bottom_right_panel = SerialMonitorWidget()
        #Output state variable to keep track of the current output state (ON/OFF)
        self.current_output_state = False

        # Create a vertical layout for the right side
        right_side_layout = QVBoxLayout()
        right_side_layout.addWidget(self.top_right_panel,stretch=1) # Takes 1 part of the height
        right_side_layout.addWidget(self.bottom_right_panel,stretch=2) # Takes 1 part of the height

        # 4. Add the left panel and the right layout to the master layout
        master_layout.addWidget(self.left_panel, stretch=1)      # Takes 1 part of the width
        master_layout.addLayout(right_side_layout, stretch=2)    # Takes 2 parts of the width

        #Add the master layout to the master master layout
        self.mastermaster_layout.addLayout(master_layout)
        # Apply the mastermaster layout
        central_widget.setLayout(self.mastermaster_layout)
        self.setCentralWidget(central_widget)

        self.setup_menu()

        #setup footer
        self.setup_footer()

        "Script Manager"

        self.script_man = ScriptManager(DEBUG_MODE)
        #wiring the script manager's log signal to the main app's message display function
        self.script_man.log_signal.connect(self.script_man_message)
        

        """Wiring Board Status"""

        # Wire the connect button click to our toggle function
        self.left_panel.btn_connect.clicked.connect(self.toggle_connection)
        
        # Wire the backend connection status directly to the left panel's UI updater
        self.board.connection_changed.connect(self.left_panel.update_connection_ui)

        #Connect freq button to the send_frequency function
        self.left_panel.btn_set_freq.clicked.connect(self.send_frequency)

        # Wire the telemetry dictionary signal directly to the left panel's new function
        self.board.telemetry_updated.connect(self.left_panel.update_telemetry)

        # Wire the telemetry dictionary signal to the save_telemetry function
        self.board.telemetry_updated.connect(self.save_telemetry)

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

        # Wire the connected signal to enable/disable slider
        self.board.connection_changed.connect(self.top_right_panel.update_slider_state) 



    def setup_menu(self):
        # 1. Create the Menu Bar
        menu_bar = self.menuBar()
        
        # 2. Add a "Scripting" Menu
        script_menu = menu_bar.addMenu("Scripting")
        
        # 3. Create Actions (Buttons in the menu)
        #create_action = QAction("Create New Script...", self)
        load_action = QAction("Load Script...", self)
        self.run_action = QAction("Run Script", self)
        
        # Disable the run button by default until a script is actually loaded
        self.run_action.setEnabled(False)
        
        
        #create_action.triggered.connect(self.create_script)
        load_action.triggered.connect(self.load_script)
        self.run_action.triggered.connect(self.run_script)
        #wire connect event to enable_run_button function 
        self.board.connection_changed.connect(self.enable_run_button)
        
        
        #script_menu.addAction(create_action)
        script_menu.addAction(load_action)
        script_menu.addSeparator() # Adds a nice visual line
        script_menu.addAction(self.run_action)
        


    def setup_footer(self):
        """Footer"""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(10, 0, 10, 5) # Tight margins
        
        version_label = QLabel(INFO)
        version_label.setStyleSheet("color: #666666; font-size: 10px;")

        max_limit_label = QLabel(f"MAX_LIMIT : {MAX_LIMIT} %")
        max_limit_label.setStyleSheet("color: #566666; font-size: 10px;")
        
        self.global_status_label = QLabel("🔴 Offline")
        self.global_status_label.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")

        #---SCRIPT PROGRESS BAR---#
        prog_layout = QHBoxLayout()
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align to the right

        self.script_progress_bar = QProgressBar()
        self.script_progress_bar.setRange(0, 100)
        self.script_progress_bar.setValue(0)
        self.script_progress_bar.setFormat("Script not loaded")
        prog_layout.addWidget(self.script_progress_bar)
        self.script_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.script_progress_bar.setFixedWidth(300)  # Set a fixed width for the progress bar
        

        #style the progress bar to have a dark theme
        self.script_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #1e1e1e;
                }

                QProgressBar::chunk {
                background-color: #0078D7;
                border-radius: 4px;        
                margin: 0px;               /* Ensures there is no invisible padding shrinking it */
                width: 1px;              
            }
            """)

        
        
        footer_layout.addWidget(version_label)
        footer_layout.addStretch()
        footer_layout.addLayout(prog_layout)
        footer_layout.addStretch() 
        footer_layout.addWidget(max_limit_label)
        footer_layout.addWidget(self.global_status_label)
        
        # Add everything to the absolute main layout
        self.mastermaster_layout.addLayout(footer_layout) 

        """Wiring Footer Status"""

        self.board.connection_changed.connect(self.update_global_status)
    
        

    def toggle_connection(self):
        """Triggered when the user clicks the Connect button on the board status panel."""
        if not self.board.is_connected:
            # Read the selected port directly from the combo box
            selected_port = self.left_panel.port_combo.currentData()
            if DEBUG_MODE:
                print(f"[DEBUG]:At main.toggle_connection: Selected port name / path (thx unix) : {selected_port}")
            
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

        """Parses the user's input, applies limits, and sends the command , checks if OUTPUT is disbled."""
        # 1. Grab the raw text and convert it to lowercase (so 'K' or 'k' both work)
        if self.current_output_state:
            if DEBUG_MODE : print(f"[DEBUG]:At main.send_frequency : Attempting to show freq warning with current OUTPUT status:{self.board.connection_changed}")
            if not self.freq_warning():
                self.bottom_right_panel.append_message("Canceled set frequency!")
                return

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

            if DEBUG_MODE:
                self.bottom_right_panel.append_sent_message(f"F:{freq_value}") 
        
            self.left_panel.freq_input.clear()  # Clear the input field after sending

        except ValueError:
            
            self.left_panel.freq_input.setText("Invalid input")

    def freq_warning(self) -> bool:
        """Warning message when user changes freq while OUTPUT is enabled"""
        #This func is bypassed when running a script
        if DEBUG_MODE : print("[DEBUG]:At main.freq_warning prompted user with freq change warning")

        buttons =  QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel

        warning = QMessageBox(parent = self)

        warning.setWindowTitle("Warning!")

        warning.setText("<b>Changing the frequency will alter the current duty cycle</b>.\nIt is reccomended to first disable the output!")
        
        warning.setInformativeText("Do you still want to proceed?")
        
        warning.setIcon(QMessageBox.Icon.Warning)

        warning.setStandardButtons(buttons)

        warning.setDefaultButton(QMessageBox.StandardButton.Cancel)

        warning_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        warning.setWindowIcon(warning_icon)

        result = warning.exec()

        return result == QMessageBox.StandardButton.Ok


    def send_limit(self):
        raw_text = self.left_panel.limit_input.text().strip()
        if not raw_text: return
        try:
            limit_val = int(raw_text)
            # Enforce 0-MAX_LIMIT bounds
            if limit_val > MAX_LIMIT: limit_val = MAX_LIMIT
            if limit_val < 0: limit_val = 0
            
            self.board.send_command(f"L:{limit_val}")

            if DEBUG_MODE:
                self.bottom_right_panel.append_sent_message(f"L:{limit_val}")
                
                
            self.left_panel.limit_input.clear()
        except ValueError:self.left_panel.limit_input.clear()

    def send_ramp(self):

        if DEBUG_MODE:
            print("[DEBUG] Ramp button clicked.")
        raw_text = self.left_panel.ramp_input.text().strip()
        print(f"[DEBUG] Raw ramp input: '{raw_text}'")
        if not raw_text: return

        #seconds input
        if raw_text.endswith('s'):
            raw_text = raw_text[:-1]  # Remove the 's' from the string
            
            try:
                ramp_val = int(raw_text)*1000  # Convert seconds to milliseconds

                if DEBUG_MODE:
                    print(f"[DEBUG] Parsed ramp value from secs func: {ramp_val}")
                    self.board.send_command(f"P:{ramp_val}") 

                self.left_panel.ramp_input.clear()
            except ValueError:
                self.left_panel.ramp_input.clear()
                print(f"[DEBUG] error:{ValueError}")
        else: #millis input

            try:
                ramp_val = int(raw_text)

                if DEBUG_MODE:
                    print(f"[DEBUG] Parsed ramp value: {ramp_val}")
                    self.bottom_right_panel.append_sent_message(f"R:{ramp_val}")

                self.board.send_command(f"P:{ramp_val}") 
                self.left_panel.ramp_input.clear()
            except ValueError:
                self.left_panel.ramp_input.clear()
                print(f"[DEBUG] error:{ValueError}")

    def send_duty(self):
            """Reads the slider and sends the target duty cycle."""
            target_val = self.top_right_panel.slider.value()
            self.board.send_command(f"D:{target_val}")
            
            if DEBUG_MODE:
                self.bottom_right_panel.append_sent_message(f"D:{target_val}")

    def toggle_output(self):
        """Checks the memorized state and sends the opposite command explicitly."""
        if self.current_output_state is True:
            
            self.board.send_command("O:0")
            if DEBUG_MODE:
                print("[DEBUG] Sent Command: 0:0 (Turn OFF)")
                self.bottom_right_panel.append_sent_message("O:0")
        else:
            
            self.board.send_command("O:1")
            if DEBUG_MODE:
                
                self.bottom_right_panel.append_sent_message("O:1")
                print("[DEBUG] Sent Command: 0:1 (Turn ON)")
    
    def save_telemetry(self, payload):
        """saves telemetry data"""
        self.current_output_state = payload["output_enabled"]
        self.latest_telemetry = payload
        
        # If the script runner is active, forward the current data to it
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.update_telemetry(payload)

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

    def load_script(self) :  

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Automated Script",
            "",
            "SEQ Scripts (*.seq *.txt);;All Files (*)"
        )
        if filepath:
            if DEBUG_MODE : print(">>>[DEBUG]:At main: load_script: Script path loading.")
            loaded_script = self.script_man.parse_file(filepath)

            if not loaded_script:
                if DEBUG_MODE : print(">>>[DEBUG]:At main: 'load_script:parse_file' returned None")
                return

           
            self.script_defaults = loaded_script.get("defaults")
            self.script_commands = loaded_script.get("commands")
            #self.run_action.setEnabled(True)  we also need to make sure that we have a valid connection to the board before enabling the run button
            self.enable_run_button() # attemkpt to enable the run button if both a script is loaded and the board is connected
            self.script_progress_bar.setFormat(f"Script loaded: {os.path.basename(filepath)}")
            if DEBUG_MODE : 
                print(f">>>[DEBUG]:At main: load_script: Script loaded successfully with {len(self.script_commands)} commands.")
                print(">>>[DEBUG]:At main: load_script: Attempting to enable run button")
        else:
            if DEBUG_MODE : print(">>>[DEBUG]:At main: load_script:returned script path is a Null string ")
            self.script_man_message("Failed to Open File!")
        

    def enable_run_button(self):
        """Enables the 'Run Script' button if a script is loaded and the board is connected."""
        if self.script_commands and self.board.is_connected:
            self.run_action.setEnabled(True)
        else:
            self.run_action.setEnabled(False)
        

    def run_script(self):
         #Map the live telemetry to the format ScriptRunner expects
        currents = {
            "FREQ": self.latest_telemetry.get("frequency", 20000),
            "RAMP": self.latest_telemetry.get("ramp_period", 3000),
            "DUTY": self.latest_telemetry.get("target_duty", 0),
            "OUT": self.latest_telemetry.get("output_enabled", False)
            }
        
        # Pass it into the thread
        self.worker = ScriptRunner(
            commands=self.script_commands, 
            defaults=self.script_defaults,
            currents=currents
        )

        self.script_progress_bar.setFormat("Running Script")
        
    # ... connect signals and start ...
        self.worker.progress_signal.connect(self.script_progress_bar.setValue)
        self.worker.finished_signal.connect(lambda: self.script_progress_bar.setFormat("Script Finished!"))
        self.worker.log_signal.connect(self.script_runner_message)
        self.worker.next_command.connect(self.board.send_command)
        self.board.telemetry_updated.connect(self.worker.update_telemetry)

        self.worker.start()

    def script_man_message(self,message):

        self.bottom_right_panel.append_sent_message(f"[SCRIPTMANAGER]:{message}")

    def script_runner_message(self,message):
    
            self.bottom_right_panel.append_sent_message(f"[SCRIPTRUNNER]:{message}")



#were done telos kalo ola kala

if __name__ == "__main__":


    print(f"{logo}\n")
    print(f"{INFO}\n")

    app = QApplication(sys.argv)
   
    # Apply the dark theme palette
    #app.setPalette(DarkPalette())
    window = MainApp()
    window.show()
    sys.exit(app.exec())
            