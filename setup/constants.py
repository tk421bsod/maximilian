import os
import sys

#Special control characters for text formatting
TEXT_END = "\x1b[0m"
TEXT_STYLES = {"none":0, "bold":1, "underline":2, "negative1":3, "negative2":5, "black":30, "red":31, "green":32, "yellow":33, "blue":34, "purple":35, "cyan":36, "white":37}

OS_TYPE = os.name
FORMATTING_ENABLED = True
IS_DEBUG = "-v" in sys.argv
MENU_LIST = ["main", "more", "database", "install", "repair", "virtual"]
