from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel , QPushButton, QLineEdit, QTextEdit

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont

class SerialMonitorWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # self.setStyleSheet("""
        #      QWidget {
        #         border: 2px solid #555555;
        #         border-radius: 20px;
        #         background-color: #2b2b2b; /* A nice dark gray panel background */
        #     }
        # """)
        #If we add a border to the parent widget it will overide the border of the card,
        # so we will not add a border to the parent widget, but only to the card (Qframe) that is inside it.
        
        

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        #create card frame to hold the text and other elements
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame {
                border: 2px solid #555555;
                border-radius: 20px;
                background-color: #2b2b2b;
            }
            QLabel { 
                border: solid; 
                background-color: transparent; 
            }
        """)
        #Creates a layout specifically for INSIDE the card (Qframe)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 20, 20, 20) # Adds padding inside the box

        main_layout.addWidget(self.card)

        """TITLE"""
        title = QLabel("<b>SERIAL MONITOR</b>")
        title.setStyleSheet("font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        #baud_rate = QLabel("MAYBE BAUD RATE?")

        """TEXT DISPLAY"""
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)

        mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono_font.setPointSize(11) # Set to a clean, readable size
        self.text_display.setFont(mono_font)

        # Give the text area its own subtle inset look
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; 
                color: #d4d4d4; 
                
                border: 1px solid #444444;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        card_layout.addWidget(self.text_display)
        
        """ --- INPUT ROW --- """
        input_row = QHBoxLayout()
        
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type direct command here...")
        self.input_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #555555; 
                border-radius: 5px; 
                padding: 5px; 
                background-color: #1e1e1e; 
                color: white;
            }
        """)
        
        self.btn_send = QPushButton("Send")
        self.btn_clear = QPushButton("Clear")
        
        input_row.addWidget(self.input_box)
        input_row.addWidget(self.btn_send)
        input_row.addWidget(self.btn_clear)
        
        card_layout.addLayout(input_row)
        
       
        #card_layout.addStretch()
        #card_layout.addWidget(baud_rate)

        self.card.setLayout(card_layout)
        self.setLayout(main_layout)

        #disable input box and send button until connected to the board
        self.input_box.setEnabled(False)
        self.btn_send.setEnabled(False)

        """-- LOCAL WIRING --"""
        # The clear button doesn't need to talk to the backend, 
        # so we can wire it directly to the text display right here!
        self.btn_clear.clicked.connect(self.text_display.clear)

    def append_message(self, message):
        """Adds a new line of text to the monitor screen."""
        self.text_display.append(message)

    def append_sent_message(self, message):
        """Formats and displays user-sent commands in blue with a '>>>' prefix."""
        # We use HTML span tags to color the text blue (#3b82f6 is a clean modern blue)
        formatted_msg = f"<span style='color: #3b82f6; font-weight: bold;'>&gt;&gt;&gt; {message}</span>"
        self.text_display.append(formatted_msg)
    
    
    def update_connection_ui(self, is_connected):
        """Enables or disables the serial monitor typing tools based on connection state."""
        self.input_box.setEnabled(is_connected)
        self.btn_send.setEnabled(is_connected)
        
        if not is_connected:
            # Optional: Clear the input box if connection drops
            self.input_box.clear()    