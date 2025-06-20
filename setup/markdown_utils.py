from .. import text

def _find_separator_pairs(source : str, separator : str):
    """Find all pairs of `separator` in the string `source`.
    Returns their indexes as a list of tuples.
    """
    pairs = []
    cur = 0
    #Find the first occurrence.
    ret = source.find(separator)
    cur = ret
    while cur < len(source):
        #If we've run out of occurrences, return the list of pairs.
        if cur == -1:
            return pairs
        #Otherwise just append the current index to the current pair.
        pair.append(cur)
        #Find the next occurrence.
        ret = source.find(separator, cur + 1)
        cur = ret
        #Add the pair to the list of pairs if it's full.
        if len(pair) == 2:
            pairs.append(pair)
            pair = []
    return pairs

def apply_markdown(text : str):
    """Apply markdown in strings to be printed. Just makes it a little easier to write things that require formatting, ya know?
    Like instead of adding style=text.TEXT_STYLES['bold'] to EVERY SINGLE print() call I can just put asterisks around the text I want formatted :)
"""
    while True:
        final = ""
        #Check for separators in our text. Replace separators with their style, then print the resulting string.
        for separator, style in [("**", f"\x1b[{text.TEXT_STYLES['bold']};39;59m"), ("~~", f"\x1b[{text.TEXT_STYLES['underline']};39;59m"), ("[red]", f"\x1b[0;{text.TEXT_STYLES['red']};59m"), ("[green]", f"\x1b[0;{text.TEXT_STYLES['green']};59m")]:
            pairs = _find_separator_pairs(text, separator)
            processed = ""
            for pair in pairs:
                #Replace the first part of the pair with a separator.
                processed += style + text[pair[0]+len(separator):pair[1]]
                #End the styled portion.
                processed += TEXT_END
                final += processed
        return final
