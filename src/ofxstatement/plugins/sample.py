from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser
from ofxstatement.statement import Statement, StatementLine, generate_transaction_id
from decimal import Decimal as D
import dateparser
import csv
import re

class SamplePlugin(Plugin):
    """Sample plugin (for developers only)
    """

    def get_parser(self, filename):
        return SampleParser(filename)


class SampleParser(StatementParser):
    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        with open(self.filename, "r") as f:
            self.input = f
            lines = [line for line in csv.reader(f)]
            field_names =lines[0]
            date_index = self.get_index_from_first_line(field_names)
            (meta, raw_records)= self.merge_lines_on_field(date_index,field_names,lines[1:])
            lines = self.to_statement_line( raw_records)
            #import pdb
            #pdb.set_trace()
            statement= Statement()
            statement.lines = lines
            return statement
    def merge_lines_on_field(self,new_record_marker_idx,field_names,lines):
        records = []
        meta = {}
        for line in lines:
            if line[0]== 'Sold initial:':
                meta["start_balance"] = line[3]
                continue
            elif line[0]== 'Sold final ': 
                meta['end_balance']= line[3]
                break #legal shit after this
            elif line[new_record_marker_idx]:
                records.append({})
            for index,(field_name, field) in enumerate( zip(field_names, line)):
                print("%i, %s, %s"%(index,field_name,field))
                field_name = field_name or 'field_%i'%index
                if not field or field == '':
                    continue
                if  field_name in records[-1]:
                    records[-1][field_name] = records[-1][field_name]  + '\n' + field
                else:
                    records[-1][field_name] =  field
        return (meta, records)
    def to_statement_line(self, raw_records):
        ret =[]
        for record in raw_records:
            date = dateparser.parse(record['Data'])
            memo = record['Detalii tranzactie']
            line = StatementLine(date=date, memo=memo)
            if 'Credit' in  record:
                line.amount = D(record['Credit'].replace('.','').replace(',','.'))
                line.trntype = 'CREDIT'
            elif 'Debit' in record:
                line.amount = D(record['Debit'].replace('.','').replace(',','.'))
                line.trntype='DEBIT'
            else:
                raise ArgumentError
            if line.trntype=='CREDIT':
                r = re.compile('ordonator:?(?P<payee>.*)$', re.MULTILINE| re.IGNORECASE)
                m = r.search( memo)
                if m:
                    d = m.groupdict()
                    line.payee = d['payee']
                    line.trntype='XFER'
                #r = re.compile('din contul:?(?P<payee>.*)$', re.MULTILINE| re.IGNORECASE)
                #m = r.search( memo)
                #if m:
                #    d = m.groupdict()
                #    line.payee = d['payee']
                r = re.compile('referinta:?(?P<refnum>.*)$', re.MULTILINE| re.IGNORECASE)
                m = r.search( memo)
                if m:
                    d = m.groupdict()
                    line.refnum = line.check_no = d['refnum']
            line.id= generate_transaction_id(line)
            ret.append(line)
        return ret

    def get_index_from_first_line(self,field_names):
        for i, name in enumerate(field_names):
            if str.lower(name) in ['data', 'date', 'datum' ]:
                return i
    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        return []

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """
        return StatementLine()
