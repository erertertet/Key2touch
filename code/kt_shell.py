import os
import mapper
import map_creator
import json

cur_file = None
MAPPER = "test.py"

if not os.path.exists("mappings"):
    os.mkdir("mappings")

def print_help():
    print("Available commands:")
    print("  - help: Show this help message")
    print("  - list: List all mapping files")
    print("  - load: Load a mapping file")
    print("  - create: Create a new mapping file")
    print("  - start: Start the mapper")
    print("  - qs: Quickstart the last mapping file")
    print("  - exit: Exit the program")

print("Welcome to the Key Mapper Shell!")
print("Type 'help' for a list of commands.")

while True:
    cmd = input("Enter command: ")

    if cmd == "help":
        print_help()

    
    elif cmd == "list":
        lst_of_files = os.listdir("mappings")
        if not lst_of_files:
            print("No mapping files found.")
            continue

        for line in lst_of_files:
            print(line)
    
    elif cmd == "load":
        temp = input("Enter the name of the mapping file to load: ")

        if temp not in os.listdir("mappings"):
            print("File not found.")
            continue
        
        cur_file = temp
    
    elif cmd == "start":
        print("press Ctrl+Q to stop the mapper")
        filename = input("Enter the name of the mapping file to start: ")
        if filename not in os.listdir("mappings"):
            print("File not found.")
            continue
        target = input("Enter the target application name: ")

        with open("quickstart.json", "w") as f:
            json.dump({"filename": filename, "target": target}, f)

        mapper.main(filename, target)
    
    elif cmd == "qs":
        if not os.path.exists("quickstart.json"):
            print("No quickstart file found.")
            continue

        with open("quickstart.json", "r") as f:
            data = json.load(f)

        filename = data["filename"]
        target = data["target"]

        if filename not in os.listdir("mappings"):
            print("File not found.")
            continue

        mapper.main(filename, target)
    
    elif cmd == "create":
        map_creator.main()
    
    elif cmd == "exit":
        print("Exiting...")
        break

    else:
        print("Unknown command. Type 'help' for a list of commands.")