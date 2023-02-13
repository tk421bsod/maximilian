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

An example:

Say you have something like:
`LQ_UPLOADED_FILE:Here's the file (at {} kbps):`
You would only translate `Here's the file (at kbps):`.
`LQ_UPLOADED_FILE` is a descriptor, which is used by Maximilian to reference the bit of text following it.
`:` is a seperator. It's used by generate.py to seperate descriptors and the text associated with them.

Please don't modify TEMPLATE unless you're adding new pairs of descriptors and text.
Thanks.
