# Badger

Badger is a tool for running parameter studies, where for a given set of
parameter values, a sequence of commands are run based on input files,
generating output that should be captured or analyzed. Badger indends, in
this setting, to replace the ubiquitous bash scripts.

## Usage

To use Badger most effectively, create a new directory for each study you'd
like to run. In this directory, add all the files you need to run your study,
as well as a file called `badger.yaml`. This file describes, essentially,
which parameter values to run, how to run a case and which output to capture
for later. Then use `badger run` to run everything automatically.

Badger stores captured data in a subdirectory called `.badgerdata`. It is
safe to delete this directory if anything should go awry. It can be
regenerated with `badger run`.

Badger tries to preserve the integrity of the data directory. If you change
the `badger.yaml` file with a non-empty data directory, Badger should detect
this and refuse to continue. To fix this, delete the data directory, or run
`badger check` for more information.

Badger stores three kinds of data from a run:

- Standard output and error from commands
- Captured files
- Data captured from standard output using regular expressions

In the first two cases, such files can be found in subdirectories of
`.badgerdata`, one subdirectory per run. For the latter, these are stored in
a structured and masked numpy array with data in `.badgerdata/results.npy`
and mask in `.badgerdata/results.mask.npy`. The easiest way to load it is by
using:

```python
from badger import Case
data = Case(path).result_array()
```

The array is masked because some runs may fail. In this case, data from those
runs are appropriately marked as missing. In the future it should be possible
to also run a subset of parameter cases.

## Structure of a badger file

The configuration file is in YAML format. The following gives a whirlwind
tour of the possibilities.

```yaml
# Define which parameters we are interested in
# Badger will run a case once for each combination of parameters, so runtime
# may be a concern
parameters:

  # Each parameter has a name and a list of values
  parameter: [1, 2, 3, 4, 5]

  # Values may be integers, floats or strings
  float-parameter: [1.2, 1.3, 1.4]
  string-parameter: [one, two, three]

  # For convenience, we can specify a uniform sampling of an interval like this
  # This should generate [0.0, 1.0, 2.0, 3.0]
  uniform-parameter:
    type: uniform
    interval: [0.0, 3.0]
    num: 4

  # There is also support for geometrically graded sampling
  graded-parameter:
    type: graded
    interval: [0.0, 1.0]
    num: 5
    grading: 1.2

# We can also define other named values, constants or expressions
evaluate:
  some-constant: 1

  # String values are interpreted as code to be evaluated
  # Parameter values defined above may be given as input
  expression: 2 * parameter

  # Previously defined values can be re-used
  new-expression: 4 / expression

# Templates are files which are read, rendered and then written to the
# temporary working directory set up for each case. When templates are
# rendered, all parameters, constants and expressions above are available.
# Template rendering is achieved using Mako:
# https://www.makotemplates.org/
# Mako is a powerful templating language, a full account of which is out of
# scope here.
templates:
  # This file has the same name in the working directory as in the source directory
  - some-template.txt

  # We can use different filenames too
  - source: input.txt
    target: output.txt

  # We can even use template substitution in the filenames
  - source: my-file-${expression}.txt
    target: output-${parameter}.txt

# Pre-files are also copied to the working directory, but no template
# substitution is performed. This is useful for e.g. binary data files.
prefiles:
  # Otherwise, the same patterns as above are all valid.
  - some-data.dat
  - source: input.dat
    target: output.dat
  - source: my-file-${expression}.dat
    target: output-${parameter}.dat

  # Globbing is supported as well
  # In this case, the target should be a relative subdirectory of the working
  # directory. The default is '.'
  - source: some-files*.txt
    mode: glob

# Post-files work the same way as pre-files, except they are copied back from
# the working directory to the data directory after the script commands are
# finished
postfiles:
  - some-output.hdf5

# This is where the magic happens. A sequence of commands to execute in the working directory
script:
  # A command may be just a string, in which case it is executed via the shell
  - some command to run with arguments

  # Template substitution is allowed here too. Shell escaping will be
  # automatically handled.
  - some command with parameter-dependend arguments ${parameter}

  # We can also specify arguments as a list, in which case the command is
  # executed as a proper subprocess, not via the shell
  - [this, is, the, right, way, to, do, it, in, my, opinion, ${parameter}]

  # More sophisticated uses require us to use this form
  - command: as above

    # A command can optionally be named. By default, the name of a command is
    # the first argument in the list of arguments (that is, the program that is
    # executed). If the program name includes a path, the path is stripped so
    # the name is just the name of the program file.
    name: some-command

    # Stdout and stderr is captured automatically if the command fails. To
    # capture it unconditionally, set this to on.
    capture-output: on

    # To record the runtime of a command, set this to on.
    capture-walltime: on

    # To capture data from stdout we have to define regular expressions
    capture:
      # Use standard Python regular expression syntax
      # https://docs.python.org/3/library/re.html#regular-expression-syntax
      # Any NAMED group will be collected and added to the result
      # This regular expression has groups named a, b and c
      - a=(?P<a>\S+) b=(?P<b>\S+) c=(?P<c>\S+)

      # By default, we find only the last of many possible matches in the
      # output.  This can be changed.
      - pattern: a=(?P<a1>\S+)
        mode: first

      # We can also collect all matches. In this case the result will be a list.
      - pattern: a=(?P<a2>\S+)
        mode: all

      # Since writing regular expressions is tediuos and error-prone, Badger has
      # some predefined ones.  In this case, we're matching integers...
      - type: integer

        # This is used as the group name
        name: somegroup

        # And this is some text that comes before the integer to match.
        # The resulting regular expression is something like:
        # someint\s*(?P<somegroup>...)
        # where ... matches an integer.
        # This prefix will be safely escaped before use
        prefix: someint

      # Badger has a predefined regular expression for floats too.
      - type: float
        name: someothergroup
        prefix: somefloat

        # First, last and all also work for these
        mode: all

# The resulting array has entries for every parameter, constant, evaluated
# expression and captured regular expression, as well as walltime for each
# command, if applicable. Badger is often able to automatically determine the
# type for each of them, but may need help.
# You can use 'badger check' to see what Badger thinks the types will be.
types:

  # In particular, Badger cannot determine the type of regular expression
  # capture groups (except predefined ones).
  # Valid values here are str, int and float
  a1: str
  a2: str

# Finally, various settings
settings:

  # To store captured stdout, stderr and files, Badger needs to know the name
  # template of a directory to store them. For uniqueness, this template should
  # use all the parameters.  Badger will warn you if this is not set.
  logdir: ${parameter}-and-so-on
```
