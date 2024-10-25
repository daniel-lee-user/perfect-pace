# perfect-pace

Repository for the perfect pace project

# Usage

Run this file using `python dp_alg.py [FLAGS]`. Use `python dp_alg.py -h` for help on usage.

Flags:

```
[REQUIRED]
-f, --file  ==> file path
-t, --time  ==> time in minutes to complete course
-p, --paces ==> total number of paces

[OPTIONAL]
-l, --loop      ==> if the course contains a loop
-s, --smoothen  ==> if the course should be smoothened              [UNIMPLEMENTED]
-r              ==> if a randomly generated course should be used   [UNIMPLEMENTED]
-h              ==> opens help menu
```

Example: `python dp_alg.py -f "data/boston.gpx" -t 180 -p 2`
