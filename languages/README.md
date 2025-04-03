Hi. This is where Maximilian's language files are stored.  
To create a new language file, make a copy of TEMPLATE and replace everything after the : on each line with its translation.  
Don't translate anything before the :.  
Once you're done, run `generate.py` with the filename of your translation to turn it into a format that Maximilian can read. This will copy your original translation to the original name + -original.  
  
A few reminders:  
- Never translate emojis, e.g <:red_x:> or \\U3827295
- Keep any {}, they'll be substituted for other stuff at run time
- Double quotes aren't allowed
- You can comment out lines by placing # at the start. This will make generate.py ignore them.
- Use double backslashes. Single backslashes will prevent Maximilian from loading your translation correctly. 
  
Here's how you should translate strings:  
  
Say you have something like:  
`LQ_UPLOADED_FILE:Here's the file (at {} kbps):`  
You would only translate `Here's the file (at kbps):`.  
`LQ_UPLOADED_FILE` is a descriptor, which is used by Maximilian to reference the bit of text following it.  
`:` is a seperator. It's used by generate.py to seperate descriptors and the text associated with them.  
The `{}` gets substituted for something else when the string is used.  
Here it's a bitrate for a converted audio file.  
These characters should be preserved, but their position in the string can change as needed.  
  
As for converting your translation:

  The template cannot be read by Maximilian and needs some additional processing before Maximilian can load it.  
  After copying the template to another file, and translating strings, it's time to convert your translation into a usable format.  
  generate.py is a script that does this for you.  
  If you're translating stuff into French, for example, and your new language file is named `fr`, you would run `python3 generate.py fr`.  
  This will overwrite `fr` with a new file in the proper format, and save your modified template to `fr-original`.  

To use your translation:
  
  There are a couple of options.  
  You can add `--language {name_of_language_file}` when running `main.py`.  
  This will switch the language used to the language file specified.  
  
  If you want to switch the language without having to type `--language` every time, add `language:{name_of_language_file}` to `config`.  
  Maximilian will load and use the language specified every time you start it, but this can be overridden by `--language`.
  
Please don't modify TEMPLATE unless you're adding new pairs of descriptors and text.  
Thanks.  
