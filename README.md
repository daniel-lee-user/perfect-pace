# perfect-pace

Repository for the perfect pace project

# Website:

https://daniel-lee-user.github.io/perfect-pace/

# Installation instructions:

If you run the website using the VSCode live server, the save directory will be located outside of this project directory (../perfect_pace_data). The reason why the save directory is outside of the repository is because live reload will automatically refresh the server whenever changes are made, preventing you from seeing your updated pacing plan.

Run the server with `python server.py` before opening the `index.html` file with liveserver in order to use the frontend.

# Usage

Run this file using `python src/main.py [FLAGS]`. Use `python src/main.py -h` for help on usage.

Flags:

```
[REQUIRED]
-f, --file  ==> file path
-t, --time  ==> time in minutes to complete course
-p, --paces ==> total number of paces
-m, --method    ==> pacing plan method to use

[OPTIONAL]
-l, --loop      ==> if the course contains a loop
-s, --smoothen  ==> if the course should be smoothened
--random        ==> if a randomly generated course should be used
-v, --verbose   ==> if the pacing plan should be generated in verbose mode
-r, --repeat    ==> if the user wants to repeat generating pacing plans
-h              ==> opens help menu
```

Example: `python src/main.py -f "data/Lakefront-Loops-5K.gpx" -t 20 -p 6 -m "BF"`
