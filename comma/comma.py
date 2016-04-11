#!/usr/bin/env python

import csv
import datetime
import os

try: 
    from StringIO import StringIO
except ImportError:
    from io import StringIO

__all__ = ("CommaDialect", "CommaRow", "Comma", "make_backup")

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
    #__slots__ = ("row", "header", "header_dict", "parsers", "serializers")
    def __init__(self, text_row=None, native_row=None, header=None, parsers=None, serializers=None):
        if not (text_row is None) ^ (native_row is None):
            raise ValueError("Supply exactly one of text_row or native_row as an argument")

        # self.row should store text type
        row = text_row if text_row is not None else native_row

        # Support header/row lists or dict format.
        if isinstance(row, dict): # Also supports OrderedDict, etc.
            # header kwarg is just ignored if row is a dict
            self.header, self.row = zip(*row.items())
        else:
            self.header = header
            self.row = row

        if self.header is not None:
            self.header_dict = dict(zip(self.header, range(len(self.header))))

        self.parsers = parsers
        self.serializers = serializers

        if native_row is not None:
            # At this point self.row contains native types, not text
            # Convert to text, self.row should only contain text type
            self.row = [self._serialize(*arg) for arg in enumerate(self.row)]

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
            except (KeyError, IndexError):
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
            if self.header is None:
                raise ValueError("Unable to perform dict-like access without specifying a header")
            try:
                serializer = self.serializers[self.header[i]]
            except (KeyError, IndexError):
                return data
            return serializer(data)
        return data

    def __len__(self):
        return len(self.row)

    def list(self):
        return self[:]

    def dict(self):
        if self.header is None:
            raise ValueError("Unable to perform dict-like access without specifying a header")
        return {self.header[i] : self[i] for i in range(len(self))}

    def __repr__(self):
        if self.header is None:
            return repr(self.list())
        return repr(self.dict())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._parse(key)
        elif isinstance(key, str):
            if self.header is None:
                raise ValueError("Unable to perform dict-like access without specifying a header")
            return self._parse(self.header_dict[key])
        elif isinstance(key, slice):
            return list(map(self._parse, range(len(self))[key]))
        raise TypeError

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.row[key] = self._serialize(key)
        elif isinstance(key, str):
            if self.header is None:
                raise ValueError("Unable to perform dict-like access without specifying a header")
            k = self.header_dict[key]
            self.row[k] = self._serialize(k, value)
        else:
            raise TypeError

class Comma(object):
    def __init__(self, _csv_file, read=True, write=True, backup=None, dialect=None, has_header=None, sniff=1024, parsers=None, serializers=None):
        if hasattr(_csv_file, 'read'):
            self.csv_file = _csv_file
            self.readable = "r" in self.csv_file.mode and read
            self.writeable = any([m in self.csv_file.mode for m in ('r+', 'w', 'a')]) and write
        else:
            self.writeable = write
            self.readable = os.path.exists(_csv_file) and read
            mode = "r+" if self.readable else "w"
            #self.csv_file = open(_csv_file, mode, newline='')
            self.csv_file = open(_csv_file, mode)

        self.buffered_output = self.readable and self.writeable

        # If mode is read/write there needs to be a separate write buffer
        self.output_stream = None
        self.input_stream = None
        if self.readable:
            self.input_stream = self.csv_file
        if self.writeable:
            if self.buffered_output:
                # Currently, there isn't a case in the code where open() is called in a way that deletes an existing file
                # so it's okay to backup the file after opening it.
                # This is not guarenteed if the __init__ logic changes. Be careful!
                if backup:
                    self.buffered_output = False
                    backup_suffix = backup if isinstance(backup, str) else None
                    output_filename, backup_filename = make_backup(self.csv_file.name, suffix_template=backup_suffix)
                    self.output_stream = self.csv_file
                    self.input_stream = open(backup_filename, self.mode.replace('w', ''))
                else:
                    self.output_stream = StringIO()
            else:
                self.output_stream = self.csv_file

        # Sniff CSV file to detect dialect. This doesn't work incredibly well...
        if sniff and self.input_stream is not None:
            sample = self.input_stream.read(sniff)
            self.input_stream.seek(0)
            sniffer = csv.Sniffer()
            if dialect is None:
                dialect = sniffer.sniff(sample, delimiters=None)
            if has_header is None:
                has_header = sniffer.has_header(sample)
        else:
            dialect = CommaDialect if dialect is None else dialect
            has_header = True if has_header is None else has_header

        self.dialect = dialect
        self.has_header = has_header

        self.parsers = parsers
        self.serializers = serializers

        if self.input_stream is not None:
            self.reader = csv.reader(self.input_stream, dialect=dialect)
        else:
            self.reader = None

        if self.output_stream is not None:
            self.writer = csv.writer(self.output_stream, dialect=dialect)
        else:
            self.writer= None

        # Read header from file
        self.header_data = None
        if self.has_header:
            if self.reader is not None:
                self.header_data = next(self.reader)
            # Maybe hold off on writing header in case user wants to modify it in some way
            #if self.writer is not None and self.header_data is not None:
            #    self.writer.writerow(self.header_data)
    
    @property
    def header(self):
        if self.has_header:
            return self.header_data
    
    @header.setter
    def header(self, header_data):
        self.has_header = True
        self.header_data = header_data

    def _text_row(self, row_data, *args, **kwargs):
        return CommaRow(*args, text_row=row_data, header=self.header_data, parsers=self.parsers, serializers=self.serializers)

    def _native_row(self, row_data, *args, **kwargs):
        return CommaRow(*args, native_row=row_data, header=self.header_data, parsers=self.parsers, serializers=self.serializers)

    def __next__(self):
        row = next(self.reader)
        return self._text_row(row)

    def next(self):
        row = next(self.reader)
        return self._text_row(row)

    def __iter__(self):
        return self

    def write_header(self):
        if self.writer is not None:
            if self.has_header:
                self.writer.writerow(self.header_data)
            # Probably don't exception to raise if a header isn't specified
        else:
            raise ValueError("Comma object mode is not writeable")

    def write_row(self, data):
        if self.writer is not None:
            row = self._native_row(data)
            self.writer.writerow(row.row)
        else:
            raise ValueError("Comma object mode is not writeable")

    def close(self):
        # Close open files, copy write buffer to read buffer.
        if self.buffered_output:
            # Copy file over
            self.input_stream.seek(0)
            self.input_stream.write(self.output_stream)
            self.input_stream.truncate()
        if self.output_stream is not None:
            self.output_stream.close()
        if self.input_stream is not None:
            self.input_stream.close()

def make_backup(original, suffix_template="%y%m%d", suffix=None):
    if suffix is None:
        suffix = datetime.datetime.now().strftime(suffix_template)

    name, _sep, ext = original.rpartition('.')
    if not name:
        # If there was no '.' in the string, name will be empty
        name, ext = ext, name
    base = "%s_{}.%s" % (name, ext)
    x = 1
    backup_file = base.format(suffix)
    while os.path.exists(backup_file):
        backup_file = base.format(suffix + "_" + x)
        if not os.path.exists(backup_file):
            break
        x += 1
    shutil.copyfile(original, backup_file)
    return original, backup_file
