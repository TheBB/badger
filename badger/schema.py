from functools import reduce
from pathlib import Path
import re

from typing import Tuple, Dict

import treelog as log

from strictyaml import (
    ScalarValidator, Optional, Any, Bool, Int, Float, Str, Map,
    MapPattern, Seq, FixedSeq, Validator, OrValidator, YAMLValidationError,
)

from strictyaml.parser import generic_load


class Deprecated(Validator):

    _message: str
    _inner: Validator

    def __init__(self, message: str, inner: Validator):
        self._message = message
        self._inner = inner

    def __call__(self, *args, **kwargs):
        log.warning(self._message)
        return self._inner(*args, **kwargs)


class Literal(ScalarValidator):
    """Validator that only matches a literal string."""

    _expected: str

    def __init__(self, expected: str):
        super().__init__()
        self._expected = expected

    def validate_scalar(self, chunk):
        if self._expected != chunk.contents:
            chunk.expecting_but_found(f"when expecting {self._expected}", "found non-matching string")
        return chunk.contents


def Choice(*args):
    """Validator that matches a choice of several literal strings."""
    return reduce(OrValidator, map(Literal, args))


def Scalar():
    """Validator that matches integers and floats."""
    return Int() | Float()


def FileMapping(glob_allowed: bool):
    """Validator that matches a file mapping: a string or a mapping with
    source and target.
    """
    if glob_allowed:
        return Str() | Map({
            'source': Str(),
            Optional('target'): Str(),
            Optional('mode'): Choice('simple', 'glob')
        })

    return Str() | Map({
        'source': Str(),
        Optional('target'): Str(),
    })


def Regex():
    """Validator that matches a regex: a mapping with pattern and optional
    mode.
    """
    return Map({
        'pattern': Str(),
        Optional('mode'): Choice('first', 'last', 'all'),
    })


def NumberCapture():
    """Validator that matches a predefined integer or float capture."""
    return Map({
        'type': Choice('integer', 'float'),
        'name': Str(),
        'prefix': Str(),
        Optional('mode'): Choice('first', 'last', 'all'),
    })


def Capture():
    """Validator that matches any of the valid capture specs."""
    return First(
        "capture",
        Str(),
        Regex(),
        NumberCapture(),
    )


class First(Validator):
    """Validator that validates against a sequence of sub-validators,
    picking the first that matches.
    """

    _validators: Tuple[Validator]

    def __init__(self, name: str, *validators: Validator):
        self._name = name
        self._validators = validators

    def __call__(self, chunk):
        for validator in self._validators:
            try:
                result = validator(chunk)
                result._selected_validator = validator
                result._validator = self
                return result
            except YAMLValidationError as e:
                pass
        else:
            raise YAMLValidationError(
                f"failed to find a valid schema for {self._name}",
                "found invalid input", chunk
            )


class Type(ScalarValidator):
    """Validator that parses a type description."""

    scalar_regex = re.compile('^(int|integer|str|string|float|floating|double)$')

    scalar_map = {
        'int': int, 'integer': int,
        'str': str, 'string': str,
        'float': float, 'floating': float, 'double': float,
    }

    def validate_scalar(self, chunk):
        if self.scalar_regex.match(chunk.contents):
            return self.scalar_map[chunk.contents]
        chunk.expecting_but_found("when expecting a valid type description", "found invalid input")


CASE_SCHEMA = Map({
    Optional('parameters'): MapPattern(
        Str(),
        First(
            "parameter",
            Seq(Scalar()),
            Seq(Str()),
            Map({
                'type': Literal('uniform'),
                'interval': FixedSeq([Scalar(), Scalar()]),
                'num': Int(),
            }),
            Map({
                'type': Literal('graded'),
                'interval': FixedSeq([Scalar(), Scalar()]),
                'num': Int(),
                'grading': Scalar(),
            })
        ),
    ),
    Optional('evaluate'): MapPattern(Str(), Str()),
    Optional('constants'): MapPattern(Str(), Int() | Float() | Str()),
    Optional('templates'): Seq(FileMapping(glob_allowed=True)),
    Optional('prefiles'): Seq(FileMapping(glob_allowed=True)),
    Optional('postfiles'): Seq(FileMapping(glob_allowed=True)),
    Optional('script'): Seq(First(
        "script command",
        Str(),
        Seq(Str()),
        Map({
            'command': Str() | Seq(Str()),
            Optional('name'): Str(),
            Optional('capture'): Capture() | Seq(Capture()),
            Optional('capture-output'): Deprecated("capture-output is deprecated (now always on)", Bool()),
            Optional('capture-walltime'): Bool(),
        }),
    )),
    Optional('settings'): Map({
        Optional('logdir'): Str(),
    }),
    Optional('types'): MapPattern(Str(), Type()),
})


def load_and_validate(text: str, path: Path) -> Dict:
    casedata = generic_load(text, schema=CASE_SCHEMA, label=path, allow_flow_style=True)
    return casedata.data
