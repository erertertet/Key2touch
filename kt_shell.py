import os
import subprocess

cur_file = None
MAPPER = "test.py"

while True:
    cmd = input("Enter command: ")

    if cmd == "help":
        print("Available commands:")
        print("  help - Show this help message")
        print("  exit - Exit the program")
        print("  list - List all active touches")
        print("  inject - Inject a touch event")
        print("  remove - Remove a touch event")
    
    elif cmd == "list":
        lst_of_files = os.listdir("mapping")
        if not lst_of_files:
            print("No mapping files found.")
            continue

        for line in lst_of_files:
            print(line)
    
    elif cmd == "load":
        temp = input("Enter the name of the mapping file to load: ")

        if temp not in os.listdir("mapping"):
            print("File not found.")
            continue
        
        cur_file = temp
    
    elif cmd == "start":
        if cur_file is None:
            print("No mapping file loaded.")
            continue
        
        subprocess.run(["python", "test.py" + cur_file])