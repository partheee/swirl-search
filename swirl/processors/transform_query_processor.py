'''
@author:     Nicodemus
@contact:    dave@swirl.today
'''
import logging as logger
logger.basicConfig(level=logger.INFO)

from abc import ABCMeta, abstractmethod

import csv
import io

from swirl.processors.processor import *
from swirl.processors.utils import clean_string

#############################################
#############################################
class TransformQueryProcessorFactory():
    @staticmethod
    def alloc_query_transform(qxf_type, name, config):
        """
        Get the query transformer based on type
        """
        if qxf_type == "rewrite":
            return RewriteQueryProcessor(name, config)
        elif qxf_type == "synonym":
             return SynonymQueryProcessor(name, config)
        elif qxf_type == "bag":
             return SynonymBagQueryProcessor(name, config)
        else:
            raise ValueError("Invalid Query Transform Processor type")

class _ConfigReplacePattern ():
    def __init__(self, pat, rep):
        self.pattern = pat
        self.replace = rep
    def __str__(self):
        return f"<<{self.pattern}>> -> <<{self.replace}>>"


class AbstractTransformQueryProcessor(QueryProcessor, metaclass=ABCMeta):
    """
    Holder for Query shared transform fuctionality and interfaces
    """


    def __init__(self, name, config):
        self._name = name
        self._config = config

    def _config_start(self):
        """Prepare to read the config as a csv"""
        try:
            csv_file = io.StringIO(self._config)
            csv_reader = csv.reader(csv_file)
        except csv.Error as e:
            logger.error(f'Exception {e} while parsing CSV ')
            return None
        return csv_reader

    def _config_next_line(self, csv_reader):
        """
        Get the next line, skip comment lines, returns None if there are no more lines
        or if an exception is thrown.
        """
        try:
            if not csv_reader:
                return None
            while (ret := next(csv_reader, None)) is not None:
                # check the first character of first filed for comment character and skip line if present
                if ret[0][0] == '#':
                    continue
                break
            return ret
        except StopIteration:
            return None
        except csv.Error as e:
            logger.error(f'Exception {e} while parsing CSV ')
            return None

    def parse_config(self):
        logger.info(f'parse config {self.type}')
        conf_lines = self._config_start()
        if not conf_lines:
            return
        n = 0
        while (cline := self._config_next_line(conf_lines)) is not None:
            n = n + 1
            self._parse_cline(cline,n)

    def _cline_is_valid(self, cline, nth, expected_num_cols):
        if not cline:
            return False # not valid, not not an error
        if expected_num_cols and len(cline) != expected_num_cols:
            logger.warning(f'ignoring malformed line {nth} in {self._name}')
            return False
        return True

    @abstractmethod
    def get_replace_patterns(self):
        """return the replace patterns"""
        pass

    @abstractmethod
    def _parse_cline(self, cline, nth):
        """ parse line and add to replace patterns """
        pass


class RewriteQueryProcessor(AbstractTransformQueryProcessor):

    """
    parse rules and based on them replace patterns in the
    input string w/ the appropriate substitution or nothing, if that is indicated
    """

    type = 'RewriteQueryProcessor'

    replace_patterns = []

    def get_replace_patterns(self):
        return self.replace_patterns

    def _parse_cline(self, cline, nth):
        """ parse line and add to replace patterns """
        if not super()._cline_is_valid(cline, nth, 2):
            return
        pats = cline[0]
        repl = cline [1]
        for p in pats.split(';'):
            self.replace_patterns.append(_ConfigReplacePattern(p.strip(), [repl.strip()]))

    def process(self):
        return clean_string(self.query_string).strip()

#############################################

class SynonymQueryProcessor(AbstractTransformQueryProcessor):

    type = 'SynonymQueryProcessor'

    replace_patterns = []

    def get_replace_patterns(self):
        return self.replace_patterns

    def _parse_cline(self, cline, nth):
        if not super()._cline_is_valid(cline, nth, 2):
            return
        self.replace_patterns.append(_ConfigReplacePattern(cline[0].strip(), [cline [1].strip()]))

    def process(self):
        return clean_string(self.query_string).strip() + " test"

#############################################

class SynonymBagQueryProcessor(AbstractTransformQueryProcessor):

    type = 'SynonymBagQueryProcessor'

    # note : different structure from the above, need to find all matches for any word
    replace_index = {}

    def get_replace_patterns(self):
        return list(self.replace_index.values())

    def _parse_cline(self, cline, nth):
        if not super()._cline_is_valid(cline, nth, None):
            return
        s_cline = [w.strip() for w in cline]
        for word in s_cline:
            if self.replace_index.get(word, None):
                logger.warn(f'word : {word} is used in multiple bags in {self._name} on the first will be kept')
                continue
            self.replace_index[word] = _ConfigReplacePattern(word,s_cline)

    def process(self):
        return clean_string(self.query_string).strip() + " test"
