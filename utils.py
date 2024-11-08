

def cprint(text: str, bkd_color: str = "cyan"):
    '''
    Prints colored bkd text to terminal.

    \033[40m - Black
    \033[41m - Red
    \033[42m - Green
    \033[43m - Yellow
    \033[44m - Blue
    \033[45m - Magenta
    \033[46m - Cyan
    \033[47m - White
    '''
    print("\033[46m" + str(text) + "\033[00m")