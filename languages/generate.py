#!/bin/python3

#Generates a language file from a more human-readable format.
#This will replace the original file with the generated data.

import sys
import os

print("Automatically fixing formatting errors.")
FIX = True

try:
    sys.argv[1]
except:
    print("You need to specify a file.")
    quit()

if sys.argv[1] == 'TEMPLATE':
    print("You can't overwrite the main template. Make a copy first!")
    quit()

intermediatelist = []
with open(sys.argv[1], 'r') as data:
    if data.read()[0] == "{":
        print("The file is already in the correct format!")
        quit()
    data.seek(0)
    for i in data.readlines():
        if i.startswith('#'):
            continue #it's a comment!
        if not i.strip():
            continue #it's a blank line!
        intermediate = i.strip().split(':', 1)
        #lmao what is this?
        #:shrug: it works
        if FIX:
            previous = None
            for (count, char) in enumerate(intermediate[1]):
                try:
                    next = intermediate[1][count+1]
                except IndexError:
                    next = intermediate[1][count]
                if char == "\\" and next != "\\" and previous != "\\":
                    print(f"Single backslash found in {intermediate[0]}.")
                    new = ""
                    for (a, b) in enumerate(intermediate[1]):
                        new += b
                        if a == count:
                            new += "\\"
                    intermediate[1] = new
                previous = char
        try:
            intermediatelist.append(f"\"{intermediate[0]}\":\"{intermediate[1]}\"")
        except:
            break
    generated = "{" + ",".join(intermediatelist) + "}"

os.replace(sys.argv[1], f"{sys.argv[1]}-original")

with open(sys.argv[1], 'x') as languagefile:
    languagefile.write(generated)

print(f"Saved output to '{sys.argv[1]}' and moved the original to '{sys.argv[1]}-original'.")
