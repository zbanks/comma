#!/usr/bin/env python

import csv

class CommaDialect(csv.Dialect):
    delimiter = ","
    doublequote = True
    escapechar = None
    lineterminator = "\r\n"
    quotechar = '"'
    quoting = csv.QUOTE_MINIMAL
    skipinitialspace = False
    strict = False

class CommaRow(object):
    __slots__ = ("row", "header", "header_dict", "parsers", "serializers")
    def __init__(self, row, header=None, parsers=None, serializers=None):
        if isinstance(row, dict):
            header, row = zip(*row.items())
        self.row = row
        self.header = header
        self.header_dict = dict(zip(header, range(len(header))))

        self.parsers = parsers
        self.serializers = serializers

    def _parse(self, i):
        r = self.row[i]
        if isinstance(self.parsers, list):
            try:
                parser = self.parsers[i]
            except IndexError:
                return r
            return parser(r)
        elif isinstance(self.parsers, dict):
            try:
                parser = self.parsers[self.header[i]]
            except KeyError, IndexError:
                return r
            return parser(r)
        return r

    def _serialize(self, i, data):
        if isinstance(self.serializers, list):
            try:
                serializer = self.serializers[i]
            except IndexError:
                return data
            return serializer(data)
        elif isinstance(self.serializers, dict):
            try:
                serializer = self.serializers[self.header[i]]
            except KeyError, IndexError:
                return data
            return serializer(data)
        return data

    def __len__(self):
        return len(row)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._parse(key)
        elif isinstance(key, str):
            return self._parse(self.header_dict[key])
        raise TypeError

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.row[key] = self._serialize(key)
        elif isinstance(key, str):
            k = self.header_dict[key]
            self.row[k] = self._serialize(k)
        raise TypeError

            


class Comma(object):
    def __init__(self, _csv_file, dialect=None, has_header=None, sniff=1024, parsers=None, serializers=None):
        if isinstance(_csv_file, str):
            csv_file = open(_csv_file)
        else:
            csv_file = _csv_file

        if sniff:
            sample = csv_file.read(sniff)
            csv_file.seek(0)
            sniffer = csv.Sniffer()
            if dialect is None:
                dialect = sniffer.sniff(sample, delimiters=None)
            if has_header is None:
                has_header = sniffer.has_header(sample)
        else:
            dialect = CommaDialect if dialect is None else dialect
            has_header = True if has_header is None else has_header

        self.csv_file = csv_file
        self.dialect = dialect
        self.has_header = has_header
        self.parsers = parsers
        self.serializers = serializers

        self.reader = csv.reader(csv_file, dialect=dialect)
        if self.has_header:
            self.header_data = next(self.reader)
        else:
            self.header_data = None
    
    @property
    def header(self):
        if self.has_header:
            return self.header_data
    
    @header.setter
    def header(self, header_data):
        self.header_data = header_data

    def __next__(self):
        row = next(self.reader)
        return CommaRow(row, header=header_data, parsers=self.parsers, serializers=self.serializers)


