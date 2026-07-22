import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout ,QPushButton,QSlider
from PyQt6.QtCore import Qt


# 1. Start the application engine (required once per app)
app = QApplication(sys.argv)


# 2. Create the main window
window = QWidget()
window.setWindowTitle("My First App")
window.resize(300, 200)

# 3. Create the UI elements (Widgets)
label = QLabel("Ready for input!")

# Create the slider, make it horizontal, and set its bounds from 0 to 100
slider = QSlider(Qt.Orientation.Horizontal)
slider.setRange(0, 100)
slider.setValue(0) # Set the starting position

# 4. Arrange the widgets vertically (Layout)
layout = QVBoxLayout()
layout.addWidget(label)

layout.addWidget(slider)

# Attach the layout container to the main window
window.setLayout(layout)



# 5. Define what happens when the slider value changes (Slot)
def update_label(value):
    label.setText(f"Duty Cycle: {value}%")  # Update the label with the current slider value

# Connect the button's click event (Signal) to the function
slider.valueChanged.connect(update_label)

# 6. Show the window and keep the app running
window.show()
sys.exit(app.exec()) #sys.exit() ensures a clean exit of the application when the window is closed. 
                     #app.exec() starts the QT event loop and system events.When it finishes, 
                     # it returns an exit code that is passed to sys.exit() to terminate the application properly. 


