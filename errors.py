import discord

class DeletionRequestAlreadyActive(discord.ext.commands.CommandError):
    pass

class DurationLimitError(discord.ext.commands.CommandError):
    def __init__(self):
        print("Maximum duration was exceeded.")

class NoSearchResultsError(discord.ext.commands.CommandError):
    def __init__(self):
        print("No search results for this song.")

class FileTooLargeError(discord.ext.commands.CommandError):
    pass
