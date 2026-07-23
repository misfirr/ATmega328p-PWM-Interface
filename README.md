# ATmega328p-PWM-Interface 

Interface & firmware for dynamically adjusting microcontroller (ATmega328p) generated PWM signals

---
# ✨About the Project


Based on the [PWM](https://github.com/terryjmyers/PWM) lib originally created by Sam Knight , modified by Terry Myers. <br>
A GUI that works in tandem with the microcontroller to provide controlled PWM outputs with:
- Configurable Ramping speed.
- Configurable Duty Cycle.
- Configurable frequency.
- Configurable safety limits (up to an absolute maximum)
- Real-Time telemetry data
- Filtered Serial Monitor

 Developed for the boost-converter workshop by IEEE SB UPATRAS. <br>

 
⬇️Install 
---
**1. Flash the Firmware**
Open the provided `.ino` file in the Arduino IDE and upload it to your ATmega328p microcontroller.

**2. Install Python Dependencies**
Ensure you have Python installed, then install the required libraries via your terminal:
```bash
pip install PyQt6 pyserial pyqt-darktheme
```





---
## ❗Changelogs 
<details>

<summary>22/7/26 v0.1.2</summary>

- Duty Cycle Slider is now **locked** if board isn't connected.
- Fixed slider telemetry data not zeroing out when board disconnected.
- Added more debugging features , **ON** by default.
- Updated README
</details>
<details>

<summary>23/7/26 v0.1.3</summary>

- MacOS compatability 
- Other bug fixes
</details>





---
## ❗ Known Issues❗
  **Changing the frequency changes the duty cycle** <br>
---

 <details>

  <summary> More</summary>

  As of release v0.1.3 , when changing the frequency  , the duty cycle changes along with it. <br>
  This is an issue with the pwm lib used in the microcontroller and the recommended solution for sensitive projects in to first : <br>
  1. Turn off the Output.
  2. Change frequency.
  3. Set new Duty Cycle.
  4. Turn on output. <br>
    <br>This is expected to be at least mitigated in the front end in the next release (if there is one).
  </details>

 
 ---
Interested in what we do?<br>
[**Join the IEEE Student Branch at UPATRAS!**](https://ieee.upatras.gr/)
