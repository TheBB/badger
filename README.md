# Badger

A simple batch runner tool. (BATCH runnER)

## Usage

    badger.py [-h] [-o OUTPUT] [-f FORMAT] file

Supported formats are `yaml` and `py`. If the format is not specified, it is
determined from the output extension, which is `output.yaml` by default.

## Dependencies

Python 3 and PyYAML.

## Configuration file

The configuration file is in YAML format. The following entries are supported.

- templates: Template files. (String or list)
- files: Additional files that the executable will need. (String or list)
- executable: The (full) path to the executable that should be run.
- cmdargs: Additional command-line arguments passed to the executable. (String
  or list)
- parameters: A list of parameters that should be varied.
- dependencies: Additional dependent variables. These are python expressions
  evaluated at runtime.
- parse: Regular expressions for searching in stdout. Python regexp syntax. Each
  defined group will end up in the output. (String or list)
- types: Defines the expected types for each output group. Valid types are `int`,
  `float`, `bool` and `str`. Default is `str`.

Most of these are optional, but `executable`, `parameters` and `parse` must be
present.

## Behaviour

For each tuple of parameters, the dependent variables are computed.

Then, in each template file and each command-line parameter, the variables
`$var` are substituted with the actual value of `var`.

The actual computation is performed in a temporary directory which is
automatically deleted.

## Example

This setup runs the command `/path/to/binary -2D -mixed file.inp` for each of
the 27 combinations of the parameters `degree`, `elements` and `timestep`. The
output contains data for `p_rel_l2`, `cpu_time` and `wall_time` for each such
combination.

Note the use of `!!str` and single quotes to avoid miscellaneous string
behaviour that makes writing regexps difficult.

    templates: file.inp
    files: file.dat
    executable: /path/to/binary
    cmdargs: -2D -mixed file.inp
    parameters:
      degree: [1, 2, 3]
      elements: [8, 16, 32]
      timestep: [0.1, 0.05, 0.025]
    dependencies:
      raiseorder: degree - 1
      refineu: elements//8 - 1
      refinev: elements - 1
      endtime: 10
    parse:
      - !!str 'Relative \|p-p\^h\|_l2 : (?P<p_rel_l2>[^\s]+)'
      - !!str 'Total time\s+\|\s+(?P<cpu_time>[^\s]+)\s+\|\s+(?P<wall_time>[^\s]+)'
    types:
      p_rel_l2: float
      cpu_time: float
      wall_time: float

## Output

The output file and format is given by the input arguments to Badger. When
applicable, the data is listed in row-major order (the last index changes most
quickly).

## TODO

- More output formats (e.g. Matlab, CSV, pure text).
- Easy access to commonly used regexps.
