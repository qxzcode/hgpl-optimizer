# HGPL plot optimizer

These two scripts work to optimize a HPGL file to decrease the amount of time a given plot takes. There are two main operations here: joining lines with start and end points that are close to another start or end point, and removing wasted pen-up traveling. The former has a degree of fuzziness that can be adjusted, set to 0, or disabled with -1 and saves a single PU/PD cycle. The latter saves time via a simple greedy algorithm by not doing unnecessary moves in between lines with the pen up.

## Usage

```
$ python3 optimize.py input-file.plt output-file.plt
```

A plot will open showing the PU paths (black lines) and PD paths (color coded in order) which must be closed to proceed.
Optimization runs and file generated.
A new plot showing the optimized run will open.
If no output file is specified and `x.plt` is the input file, `x-opt.plt` will be output.
