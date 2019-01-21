"""
Contains the StreamSurvey class, which reads and formats raw survey data as well
as additional helper classes.
"""

import logging
import re

import numpy as np
import pandas as pd

from . import streamexceptions

class StreamSurvey(object):
    
    """
    Reads in a geomorphic survey and formats it for further use.
    
    Attributes:
        file(str): name or filepath of the csv that contains the survey data.
        sep(str): the separating character in the file.
        keywords(dict): a dictionayr that relates keywords in the survey descriptions to geomorphic features.
        data(pandas.core.frame.DataFrame): pandas dataframe representing the imported survey.
    """
    
    def __init__(self,file,sep=',',keywords=None,colRelations=None):
        """
        file(str): name or filepath of the csv that contains the survey data.
        sep(str): the separating character in the file.
        keywords(dict): a dictionary that relates geomorphic features to how they were called out in the survey.
                        If nothing is passed, a default dictionary is used.
        colRelations(dict): a dictionary that relates standardized names used by the parser to the column names of the survey.
                            If nothing is passed, a default dictionary is used.
        """
        self.file = file
        if keywords is None:
            self.keywords = {'Profile':'pro', #mandatory
                             'Cross Section':'xs', #mandatory
                             'Riffle':'ri',
                             'Run':'ru',
                             'Pool':'po',
                             'Glide':'gl',
                             'Top of Bank':'tob',
                             'Bankfull':'bkf',
                             'Water Surface':'ws',
                             'Thalweg':'thw',
                             'breakChar':'-', #mandatory
                             'commentChar':'_' #mandatory
                             }
        else:
            self.keywords = keywords
        
        if colRelations is None:
            self.colRelations = {'shotnum':'Name',
                                 'whys':'Northing',
                                 'exes':'Easting',
                                 'zees':'Elevation',
                                 'desc':'Description',
                                 }
        else:
            self.colRelations = colRelations
            
        self.sep = sep
            
        self.importSurvey()
        
    def importSurvey(self):
        df=pd.read_csv(self.file, sep=',')
        self.data = df
        
    def writeSurvey(self,name,parse = True):
        """
        Writes the survey data to a csv. If parsed is true, cross sections and profiles
        will be written to separate files.
        """
        if parse:
            raise NotImplementedError('Parsing not yet implemented.')
        else:
            self.data.to_csv(name)
            
    def parseNames(self):
        """
        Parses the survey using the desc column.
        """
        pass
    
class Parser(object):
    """
    Parses desc strings.
    """
    
    def __init__(self,parseDict):
        self.parseDict = parseDict
        
    def dictSplit(self,string):
        """
        Breaks the desc string into its name, descriptors and comment (if any)
        """
        result = {'name':None,
                  'descriptors':[None],
                  'comment':None
                 }
        
        breakChar = self.parseDict['breakChar']
        commentChar = self.parseDict['commentChar']
        
        splitAtComment = string.split(commentChar)
        try:
            result['comment'] = splitAtComment[1]
        except IndexError:
            pass
            
        splitByBreaker = splitAtComment[0].split(breakChar)
        result['name'] = splitByBreaker[0]
        try:
            result['descriptors'] = splitByBreaker[1:]
        except IndexError:
            pass
        
        return(result)
    
    def string_is_in(self,matchString,string):
        """
        Returns true if matchString is in string.
        """
        contained = re.search(matchString,string)
        if contained:
            return True
        else:
            return False
        
    def key_is_in(self,key,string):
        return(self.string_is_in(self.parseDict[key],string))
    
    def get_meaning(self,string):
        """
        Gets the semantic meaning of the dictionary returned by self.dictSplit.
        """
        result = {'type':None, # profile or cross section
                  'morphs':[], # depends on if type is profile or cross section
                  'name':None,
                  'full':string
                 }
        splitDict = self.dictSplit(string)
        result['name'] = splitDict['name']
        
        if self.key_is_in('Profile',result['name']):
            result['type'] = 'Profile'
        elif self.key_is_in('Cross Section',result['name']):
            result['type'] = 'Cross Section'
            
        for descriptor in splitDict['descriptors']:
            for key,pattern in self.parseDict.items():
                if self.string_is_in(pattern,descriptor):
                    result['morphs'].append(key)
        
        return(result)
        
        
    
    
    