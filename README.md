# perfect-pace

Repository for the perfect pace project

# Usage

Run this file using `python main.py [FLAGS]`. Use `python main.py -h` for help on usage.

Flags:

```
[REQUIRED]
-f, --file  ==> file path
-t, --time  ==> time in minutes to complete course
-p, --paces ==> total number of paces
-m, --method    ==> pacing plan method to use ("brute_force", "linear_programming")

[OPTIONAL]
-l, --loop      ==> if the course contains a loop
-s, --smoothen  ==> if the course should be smoothened              [UNIMPLEMENTED]
-r              ==> if a randomly generated course should be used   [UNIMPLEMENTED]
-h              ==> opens help menu
```

Example: `python src/main.py -f "data/Lakefront-Loops-5K.gpx" -t 20 -p 6 -m "brute_force"`
