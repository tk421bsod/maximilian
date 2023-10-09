#Generates a language file from a more human-readable format.
#This will replace the original file with the generated data.

import sys
import os

try:
    sys.argv[1]
except IndexError:
    print("You need to specify a file.")
    quit()

if sys.argv[1] == 'TEMPLATE':
    print("You can't overwrite the main template. Make a copy first!")
    quit()

intermediatelist = []
try:
    with open(sys.argv[1], 'r') as data:
        if data.read()[0] == "{":
            print("The file is already in the correct format!")
            quit()
        data.seek(0)
        for i in data.readlines():
            if i.startswith('#'):
                continue
            if not i.strip():
                continue 
            intermediate = i.strip().split(':', 1)
            try:
                intermediatelist.append(f"\"{intermediate[0]}\":\"{intermediate[1]}\"")
            except:
                break
        generated = "{" + ",".join(intermediatelist) + "}"
except FileNotFoundError:
    print("That language file doesn't exist.")
    quit()

os.replace(sys.argv[1], f"{sys.argv[1]}-original")

with open(sys.argv[1], 'x') as languagefile:
    languagefile.write(generated)

print(f"Saved output to '{sys.argv[1]}' and moved the original to '{sys.argv[1]}-original'.")
