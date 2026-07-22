from PyQt6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QGridLayout, 
                             QLabel, QSlider, QProgressBar)
from PyQt6.QtCore import Qt

class DutyCycleWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- CARD SETUP ---
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
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 20, 20, 20)

        # --- TITLE & READOUT LABELS ---
        title = QLabel("<b>DUTY CYCLE CONTROL</b>")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        card_layout.addWidget(title)

        # This label provides exact numbers since the slider is visual
        self.val_label = QLabel("Target: 0%  |  Current: 0%")
        self.val_label.setStyleSheet("font-family: monospace; font-size: 14px; color: #3b82f6; font-weight: bold;")
        card_layout.addWidget(self.val_label)

        # --- THE OVERLAY TRICK ---
        # A QGridLayout lets us assign multiple items to the exact same (Row, Column)
        overlay_layout = QGridLayout()
        overlay_layout.setContentsMargins(0, 10, 0, 10)

        # 1. BOTTOM LAYER: The Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False) # Hide default text
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 12px;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #0078D7; /* The climbing blue bar */
                border-radius: 11px;
            }
        """)
        
        # 2. TOP LAYER: The Tactile Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        
        # Add tactile ticks below the track
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.setSingleStep(1) # Point-by-point tactile control
        
        self.slider.setFixedHeight(40) # Taller than progress bar to fit the ticks
        self.slider.setStyleSheet("""
            QSlider {
                background: transparent; /* Makes the widget background invisible */
            }
            QSlider::groove:horizontal {
                background: transparent; /* Makes the track invisible so progress bar shows */
                height: 24px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #888888;
                width: 18px;
                margin: -4px 0; /* Pushes the handle slightly outside the track */
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #3b82f6;
                border: 2px solid white;
            }
        """)

        # Add BOTH to row 0, column 0. The one added LAST goes on TOP.
        overlay_layout.addWidget(self.progress_bar, 0, 0)
        overlay_layout.addWidget(self.slider, 0, 0)

        card_layout.addLayout(overlay_layout)

        #card_layout.addStretch() # Pushes everything neatly to the top
        self.card.setLayout(card_layout)
        main_layout.addWidget(self.card)
        self.setLayout(main_layout)

        # Local wiring: Instantly update the label when you drag, before sending to Arduino
        self.slider.valueChanged.connect(self.update_local_label)

    def update_local_label(self, target_val):
        """Updates the label instantly while dragging."""
        current_val = self.progress_bar.value()
        self.val_label.setText(f"Target: {target_val}%  |  Current: {current_val}%")

    def update_telemetry(self, payload):
        """Called by the main brain. Updates the climbing blue progress bar."""
        live_current = payload["current_duty"]
        live_target = payload["target_duty"]
        live_limit = payload["safety_limit"]
        out_enabled = payload["output_enabled"] # Grab the limit
        

        #Limit the slider and progress bar to the safety limit to prevent user from exceeding it

        #Update maximus dynamically to the safety limit, so the user can see the full range of motion available to them
        self.slider.setMaximum(live_limit)
        self.progress_bar.setMaximum(live_limit)
        
        #always update the progress bar to the live current value
        self.progress_bar.setValue(live_current)

        #Jitter Fix skips updating the slider if the user is actively dragging it
        if self.slider.isSliderDown():
            return
        if out_enabled :
            #Rounding fix for res problems
            diff = abs(self.slider.value() - live_target)
            
            if  diff > 1:
                self.slider.setValue(live_target)

        

        self.val_label.setText(f"Target: {self.slider.value()}%  |  Current: {live_current}%")

        # We now use the SLIDER'S position as the text value, guaranteeing 
        # your target says 25%, even if the Arduino calculates 24% or is turned OFF!

        #self.val_label.setText(f"Target: {live_target}%  |  Current: {live_current}%  |  Max: {live_limit}%")
