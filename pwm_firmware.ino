
// PWM experimentation , FW 0.1 , 21/7/26
// ATmega328p 
// IEEESBUPATRAS , PES CHAPTER
// Based on the PWM.h lib originally created by Sam Knight , modified by Terry Myers

#include <PWM.h>

int out = 9;                //D9 pwm OUT
int32_t frequency = 50000;  //Default Frequency

// Ramping variables
int current_duty = 0;       // The actual current output (0-255)
int target_duty = 0;        // The goal output we want to reach
int start_duty = 0;         // The duty cycle when the ramp started

int safety_limit = 25;      // Maximum duty cycle allowed (0-100%)
const int ABSOLUTE_MAX = 90; // The safety_limit can never go above this.

unsigned long ramp_duration = 3000; // 3000ms = 3 seconds to complete a ramp
unsigned long ramp_start_time = 0;
bool is_ramping = false;

// Print timer
unsigned long last_print_time = 0;

// Output Master Switch
bool output_enabled = false;
//saved target_pct for when output is turned off and on
int saved_target_pct = 0;

// This is a standard C++ trick to restart an Arduino. 
// It creates a function pointer that points to memory address 0 (the start of the program).
void(* resetFunc) (void) = 0;

void setup() {
  Serial.begin(9600);
  InitTimersSafe(); 

  bool success = SetPinFrequencySafe(out, frequency);
  //String logo = "██ ███████ ███████ ███████ \n██ ██      ██      ██      \n██ █████   █████   █████   \n██ ██      ██      ██      \n██ ███████ ███████ ███████"; deprecated in favor of standard ascii chars
  String logo = "## ###### ###### ###### \n## ##     ##     ##     \n## #####  #####  #####  \n## ##     ##     ##     \n## ###### ###### ######";
  if(success) {
    Serial.println(" ");
    Serial.println(logo);
    Serial.println(" ");

    Serial.println(">>>System Ready.");
    Serial.println(">>>ATmega328p");
    Serial.println(">>>--- IEEE SB UPATRAS , PES CHAPTER --- ");
    Serial.println(">>> ");
    Serial.println(">>>PWM experimentation , FW 0.1 , 21/7/26 ");
    Serial.println(">>>Based on the PWM.h lib originally created by Sam Knight , modified by Terry Myers");
    Serial.println(">>>");
    Serial.println(">>>Commands: D:val (Duty), L:val (Limit), P:val (Period ms), F:val (Freq Hz)");
    Serial.println(">>>");
  }
}

void loop() {
  // 1. Constantly check if the user typed something new
  checkSerialCommands();
  
  // 2. Smoothly update the PWM if a ramp is in progress
  updateRamp();

  // 3. Print the telemetry twice a second
  if (millis() - last_print_time >= 500) {
    // Format: T:current_duty,target_duty,safety_limit,ramp_duration,frequency,output_enabled
    Serial.print("T:");
    Serial.print(current_duty * 100 / 255);
    Serial.print(",");
    Serial.print(target_duty * 100 / 255); 
    Serial.print(",");
    Serial.print(safety_limit);
    Serial.print(",");
    Serial.print(ramp_duration);
    Serial.print(",");
    Serial.print(frequency);
    Serial.print(",");
    Serial.println(output_enabled); 
    
    last_print_time = millis();
  }
}

// --- NEW COMMAND PARSER ---
void checkSerialCommands() {
  if (Serial.available() > 0) {
    // Read the entire incoming line until the Newline character
    String input = Serial.readStringUntil('\n');
    input.trim(); // Clean up any extra spaces or hidden carriage returns

    // Make sure we actually received something like "D:75" (at least 3 characters)
    if (input.length() >= 3 && input.charAt(1) == ':') {
      
      char command = input.charAt(0);           // Extract the 'D', 'L', etc.
      long value = input.substring(2).toInt();  // Extract the number after the ':'

      switch (command) {
        
        case 'D': // SET DUTY CYCLE
          if (output_enabled){ //output enabled check
            setTargetDuty(value);
          } else {
            saved_target_pct = constrain(value, 0, safety_limit); //save target duty_pct for when output is enabled
            Serial.println(">>> Set target duty cycle for when output is enabled!");
          }
          break;

        case 'L': // SET SAFETY LIMIT
          // Constrain the new limit between 0 and our ABSOLUTE_MAX (90)
          safety_limit = constrain(value, 0, ABSOLUTE_MAX);
          Serial.print(">>> Safety Limit updated to: ");
          Serial.print(safety_limit);
          Serial.println("%");

          // CRITICAL SAFETY CHECK: 
          if ((target_duty * 100 / 255) > safety_limit) {
              Serial.println(">>> Target exceeds new limit! Forcing ramp down...");
              setTargetDuty(safety_limit); 
          }
          break;

        case 'P': // SET RAMP PERIOD
          ramp_duration = value;
          Serial.print(">>> Ramp period updated to: ");
          Serial.print(ramp_duration);
          Serial.println(" ms");
          break;

        case 'F': // SET FREQUENCY
          frequency = value;
          SetPinFrequencySafe(out, frequency); // <PWM.h> magic!
          Serial.print(">>> PWM Frequency updated to: ");
          Serial.print(frequency);
          Serial.println(" Hz");
          break;

        case 'R': // RESTART
          if (value == 1) {
            Serial.println(">>> Software Reset Triggered...");
            setTargetDuty(0);//this shi dont work it just resets the pro counter but doenst have time to zero the output , hard reset seems most unwise hmmmmm
            delay(500); // Give the serial port time to send the message
            resetFunc(); // Jump to memory address 0
          }
          break;

        case 'O': //OUTPUT PWM
          output_enabled = (bool) value;

          if (!output_enabled){
            saved_target_pct = (target_duty * 100) / 255;
            setTargetDuty(0);
            Serial.println(">>> Output Disabled :(");
           
          }
          else {
            setTargetDuty(saved_target_pct);
            Serial.println(">>> Output Enabled!");
          }
          break;

        default:
          Serial.println(">>> Error: Unknown Command Prefix!");
          break;
      }
    }
  }
}

// --- DUTY CYCLE LOGIC ---
void setTargetDuty(int input_pct) {
  // Limit the input to the dynamic safety bounds
  input_pct = constrain(input_pct, 0, safety_limit);
  
  int new_target = (input_pct * 255) / 100;
  
  if (new_target != target_duty) {
    start_duty = current_duty; 
    target_duty = new_target;
    ramp_start_time = millis();
    is_ramping = true;
    
    Serial.print(">>> Ramping to new target: ");
    Serial.print(input_pct);
    Serial.println("%");
  }
}

// --- RAMPING LOGIC ---
void updateRamp() {
  if (is_ramping) {
    unsigned long current_time = millis();
    unsigned long elapsed_time = current_time - ramp_start_time;
    
    if (elapsed_time >= ramp_duration) {
      current_duty = target_duty;
      is_ramping = false;
      Serial.println(">>> Ramp complete!");
    } 
    else {
      long duty_difference = target_duty - start_duty;
      current_duty = start_duty + (duty_difference * (long)elapsed_time) / (long)ramp_duration;
    }
    
    pwmWrite(out, current_duty);
  }
}