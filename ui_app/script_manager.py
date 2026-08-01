import os,time
from PyQt6.QtCore import QThread, QObject ,pyqtSignal

RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
RST = '\033[0m'



class ScriptManager(QObject):
    """Class for managing , loading & parsing **.seq** scripts"""
    log_signal = pyqtSignal(str)

    def __init__(self,debug=True):

        super().__init__()

        self.debug = debug

        self.defaults = {
            "STEP": 3000,
            "FREQ": 50000,
            "LIMIT": 30,
            "RETURN": False
        }

        

        self.commands = []

        self.counter = 0

        self.standard_cmds = ["RAMP" , "FREQ" , "DUTY" ,"OUT","LIMIT","RETURN","WAIT","STEP"]

        self.is_loaded = False

        #ERRORS

        self.derror = "Error parsing DEFAULT values"
        self.lerror = "Error when loading script"
        self.cerror = "Error parsing command"

        #
        self.gen_error = "Generic Error"

    def parse_file(self, filepath: str) -> dict:
            """
            Reads the .seq file and extracts defaults and commands.
            Returns a dictionary containing both.
            """
            name = os.path.basename(filepath)
            self.log_signal.emit(f"Parsing file: {name}")
            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptmanager.parse_file: parsing file: {filepath}")

            if not filepath.endswith(".seq"):
                self.parse_fail("L0:Invalid fyle type")
                if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptmanager.parse_file: file {filepath} is not a .seq file")
                return False

            self.commands.clear()
            in_execution_block = False

            
            with open(filepath, 'r') as file:

                for line in file:
                    self.counter += 1

                    #Strip comments: split by # and keep everything before it
                    clean_line = line.split('#')[0].strip().upper()
                    
                    #Skip completely empty lines
                    if not clean_line:
                        continue
                    
                    # Handle the BEGIN and END block markers
                    if clean_line == "BEGIN":
                        in_execution_block = True
                        continue
                    elif clean_line == "END":
                        in_execution_block = False
                        self.is_loaded = True
                        self.counter = 0 #reset counter
                        break  # Stop parsing after END

                    #Tokenize the line by spaces ("RAMP 4000" -> ["RAMP", "4000"])
                    tokens = clean_line.split()
                    cmd = tokens[0]

                    if cmd == "DEFAULT":
                        if not self._parse_default(tokens):
                             return { }
                    # Process commands if we are inside the BEGIN block

                    elif in_execution_block:
                        if not self._parse_command(tokens):
                            return { }

                if not self.commands:
                    print(f">>>{YELLOW}No commands parsed (is the file empty?){RST}")
                    self.log_signal.emit("No commands parsed (is the file empty?)")
                    return { }
            
            return {
                "defaults": self.defaults,
                "commands": self.commands
            }

    def _parse_default(self, tokens: list):
            """Helper to parse DEFAULT definitions and assign the correct data types."""

            if self.debug: print(f"{BLUE}[DEBUG]:{RST}At scriptmanager._parse_default: parsing default: {tokens}")

            if len(tokens) >= 3:
                key = tokens[1]
                val = tokens[2]
                
                if key == "STEP" or key == "LIMIT":
                    self.defaults[key] = int(val)
                
                elif key == "FREQ":
                    # Handle the 'k' suffix for kilohertz
                    if val.endswith('K'):
                        self.defaults[key] = int(float(val[:-1]) * 1000)
                    else:
                        self.defaults[key] = int(val)
                
                elif key == "RETURN":
                    self.defaults[key] = (val == "TRUE")

            else:
                self.parse_fail("D1 : wrong syntax")
                return False

            return True
            

    def _parse_command(self, tokens: list):
        """Helper to parse hardware commands and their arguments."""
        cmd = tokens[0]
        args = tokens[1:] if len(tokens) > 1 else []

        if self.debug : print(f">>>Parsing cmd : {cmd} {args[0]}")

        if cmd not in self.standard_cmds:

            self.parse_fail(f"C0:Invalid Command: {cmd} {args[0]}")
            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptmanager._parse_command: cmd {cmd} not in standard list :{self.standard_cmds} ")

            return False #if something goes wrong return false

        # Store arguments as a list of strings if they exist, otherwise empty list
          

        if (len(args) !=1) or (cmd == "OUT" and not(args[0] in ("ON","OFF"))) : 

            self.parse_fail("C1:Invalid arguments given")
            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptmanager._parse_command: too many args  ")
            return False
        

        self.commands.append({
            "action": cmd,
            "args": args            
            })

        return True #return true f everything is lovely :)

    def parse_fail(self,code : str):
        """print error to terminal and log"""
       
        self.is_loaded = False

        self.log_signal.emit("Failed parsing script")
        print(f"{RED}>>>Failed parsing script{RST}")

        match code[0]:

            case "D":
                self.log_signal.emit(self.derror)
                print(f"{RED}>>>{RST}{self.derror}")  

            case "L":
                self.log_signal.emit(self.lerror)
                print(f"{RED}>>>{RST}{self.lerror}")  

            case "C":
                self.log_signal.emit(self.cerror)
                print(f"{RED}>>>{RST}{self.cerror}")

            case _ :
                self.log_signal.emit(self.gen_error)
                print(f"{RED}>>>{RST}{self.gen_error}")

        self.log_signal.emit(f"Error code: {code} at line : {self.counter}")
        print(f"{RED}>>>{RST}Error code: {RED}{code}{RST} at {BLUE}line : {self.counter}{RST}")



class ScriptRunner(QThread):
    """Background thread for executing the parsed commands sequentially."""
    
    log_signal = pyqtSignal(str)        
    progress_signal = pyqtSignal(int)   
    finished_signal = pyqtSignal()  
    next_command =   pyqtSignal(str)

    def __init__(self, commands, defaults,currents,debug=True,safemode=True ,parent=None):
        super().__init__(parent)

        self.safemode = safemode
        self.currents = currents
        self.debug = debug

        self.commands = commands
        self.defaults = defaults
        self.is_running = False
        self.live_telemetry = {}  # Initialize live telemetry as an empty dictionary

    def update_telemetry(self, payload):
        """This gets called by the main GUI every time new serial data arrives"""
        self.live_telemetry = payload  

    def wait_for_target_duty(self,target):
        """Smart loop that blocks the thread until current_duty reaches 0"""
        self.log_signal.emit("Waiting for current duty to reach 0...")
        
        while self.is_running:
            # Safely get the current duty. If telemetry hasn't arrived yet, default to -1 so we keep waiting.
            current_duty = self.live_telemetry.get("current_duty", -1)
            
            if current_duty == target:
                self.log_signal.emit(f"Duty reached {target} %. Proceeding!")
                break
                
            
            time.sleep(0.1)

    def run(self):
        self.progress_signal.emit(0)

        self.is_running = True
        #--- PREPARING RUN ---
        self.log_signal.emit("Preparing run...")

        self.next_command.emit("O:0")#needs to wait for current duty to reach 0

        self.wait_for_target_duty(0)

        self.next_command.emit("D:0")
        time.sleep(0.2)
        #---setting defaults---
        default_freq = self.defaults.get("FREQ")
        self.next_command.emit(f"F:{default_freq}")

        default_limit = self.defaults.get("LIMIT")
        self.next_command.emit(f"L:{default_limit}")

        #self.log_signal.emit(f"Setting default frequency to {default_freq} Hz")

        total_commands = len(self.commands)
        print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: started execution of {total_commands} commands")

        self.log_signal.emit(f"Executing {total_commands} commands...")

        for index, cmd_dict in enumerate(self.commands):
            
            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: executing command {index}/{total_commands}: {cmd_dict}")

            if not self.is_running:
                self.log_signal.emit(":Script aborted.")
                if self.degug: print("scriptrunner.is_running false <3")

                break

            action = cmd_dict["action"]
            args = cmd_dict["args"]

            # --- EXECUTION LOGIC ---

            match action :

                case "WAIT":
                    delay_ms = int(args[0])
                    
                    self.log_signal.emit(f":Waiting {delay_ms} ms...")

                    percent = int(((index + 1) / total_commands) * 100)
                    self.progress_signal.emit(percent)

                    if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: percent completed : {percent}%")
                    time.sleep(delay_ms / 1000.0)
                    continue

                case "STEP":
                    step_ms = int(args[0])
                    
                    self.log_signal.emit(f":Stepping {step_ms} ms...")

                    percent = int(((index + 1) / total_commands) * 100)
                    self.progress_signal.emit(percent)
                    
                    time.sleep(step_ms / 1000.0)
                    continue

                case "DUTY":

                    target_duty = int(args[0])
                        
                    self.log_signal.emit(f":Setting duty cycle to {target_duty}%")
                       
                    self.next_command.emit(f"D:{target_duty}")

                    #skip if next command is step
                    if index + 1 < total_commands and self.commands[index + 1]["action"] in("STEP","WAIT"):
                        percent = int(((index + 1) / total_commands) * 100)
                        self.progress_signal.emit(percent)
                        continue

                case "RAMP":

                    ramp_period = int(args[0])

                    self.log_signal.emit(f":Setting ramp period to {ramp_period}ms")

                    if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: sending ramp command P:{ramp_period} ms")                       
                    self.next_command.emit(f"P:{ramp_period}")

                    if index + 1 < total_commands and self.commands[index + 1]["action"] in("STEP","WAIT"):
                                            percent = int(((index + 1) / total_commands) * 100)
                                            self.progress_signal.emit(percent)
                                            continue

                case "OUT":

                    out_state = args[0]
                    if out_state == "ON": 
                        self.log_signal.emit(":Setting OUT to ON")
                        self.next_command.emit("O:1")

                    elif out_state == "OFF":
                        self.log_signal.emit(":Setting OUT to OFF")
                        self.next_command.emit("O:0")

                    else:
                        self.log_signal.emit(":Unexpected error when setting output , stopping script...")
                        break

                    if index + 1 < total_commands and self.commands[index + 1]["action"] in("STEP","WAIT") :
                                            percent = int(((index + 1) / total_commands) * 100)
                                            self.progress_signal.emit(percent)
                                            continue

                case "LIMIT":
                    limit = args[0]
                    self.log_signal.emit(f":Attempting to set limit to : {limit}")
                    self.next_command.emit(f"L:{limit}")

                    if index + 1 < total_commands and self.commands[index + 1]["action"] in("STEP","WAIT") :
                                            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: sending limit command L:{limit} ")
                                            percent = int(((index + 1) / total_commands) * 100)
                                            self.progress_signal.emit(percent)
                                            
                                            continue

                case "FREQ":
                    freq = args[0]
                    self.log_signal.emit(f":Attempting to set freq to : {freq}")
                    self.next_command.emit(f"F:{freq}")

                    if index + 1 < total_commands and self.commands[index + 1]["action"] in("STEP","WAIT") :
                                            if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: sending freq command F:{freq} ")
                                            percent = int(((index + 1) / total_commands) * 100)
                                            self.progress_signal.emit(percent)
                                            
                                            continue

                case _ :
                    if self.safemode:
                        self.log_signal.emit(f":Warning , encountered unknown command that went through the parser {action}\nABORTING SCRIPT")
                        break
                    else:
                        self.log_signal.emit(f":Warning , skipped unknown command {action}")


            #Default step delay between commands

            
            step = self.defaults.get("STEP", 1000)#ms

            time.sleep(step / 1000.0)
            self.log_signal.emit(f":(DEFAULT) Stepping {step} ms...")
            

            # Update progress
            percent = int(((index + 1) / total_commands) * 100)
            self.progress_signal.emit(percent)

        #---RETURN TO ORIGINAL VALUES---
        if self.defaults.get("RETURN",True):

            self.log_signal.emit(":Returning to original values")

            orig_lim = self.currents.get("safety_limit",20)
            self.next_command.emit(f"L:{orig_lim}")
            time.sleep(0.2)

            self.next_command.emit("O:0")
            self.wait_for_target_duty(0)#needs to wait for current duty to reach 0

            orig_freq = self.currents.get("frequency",False)
            if (orig_freq) :
                self.next_command.emit(f"F:{orig_freq}")
            time.sleep(0.2)

            orig_ramp = self.currents.get("ramp_period",3000)
            self.next_command.emit(f"R:{orig_ramp}")
            time.sleep(0.2)
            orig_duty = self.currents.get("current_duty")
            self.next_command.emit(f"D:{orig_duty}")
            time.sleep(0.2)

            orig_out = self.currents.get("OUT",False)
            if orig_out : self.next_command.emit("O:1")

            self.log_signal.emit("Original values set")

            
        self.log_signal.emit("Script execution finished.")
        self.finished_signal.emit()
        self.is_running = False
        if self.debug : print(f"{BLUE}[DEBUG]:{RST}At scriptrunner.run: script finished , is_running set to false")
    
    def stop(self):
        self.is_running = False


###---PARSING TEST---

if __name__ == "__main__":

    test_manager = ScriptManager(debug=True)

    test_dict = test_manager.parse_file(filepath="scriptexample.seq")

    #print(test_dict)