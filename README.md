# perfect-pace

Repository for the perfect pace project

To install the requirements for the UI use `npm install` within the app directory

# Usage

Run this file using `python pacing_plan.py [FLAGS]`. Use `python pacing_plan.py -h` for help on usage.

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

Example: `python dp_alg.py -f "data/Lakefront-Loops-5K.gpx" -t 30 -p 8`
