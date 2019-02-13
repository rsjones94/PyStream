"""
Contains the Profile class and helper classes.
"""

import functools
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import streamexceptions
from . import streamconstants as sc
from . import streammath as sm

class Profile(object):
    """
    A longitudinal stream profile.
    
    Attributes:
        df
        metric
        name
        unitDict
    """
    
    basicCols = ['exes','whys','Thalweg']
    fillCols = ['Water Surface', 'Bankfull', 'Top of Bank']
    morphCols = ['Riffle','Run','Pool','Glide','Unclassified']
    
    def __init__(self, df, name = None, metric = False):
        """
        Args:
            df: a dict or pandas dataframe with at least three columns/keys "exes", "whys", "Thalweg"
                and additional optional columns/keys. Standardized col/key names are 
                "Water Surface", "Bankfull", "Top of Bank", "Riffle", "Run", "Pool", "Glide", "Unclassified".
                If df is passed as a dict, it will be coerced to a Pandas dataframe.
            metric: a bool indicating if units are feet (False) or meters (True)
        
        Raises:
            x
        """
        if isinstance(df,dict):
            df = pd.DataFrame.from_dict(df)
        self.df = df
        self.filldf = df.copy()
        self.metric = metric
        self.name = name
        
        if self.metric:
            self.unitDict = sc.METRIC_CONSTANTS
        elif not(self.metric):
            self.unitDict = sc.IMPERIAL_CONSTANTS
        
        self.validate_df()
        if not 'Station' in self.df: # if there is no stationing column, generate it and interpolate the cols
            self.generate_stationing()
            self.fill_columns()
            self.make_unclassified()
            self.create_features()
            
        self.calculate_profile_statistics()
        
    def calculate_profile_statistics(self):
        self.make_length()
        
    def validate_df(self):
        if not all(x in self.df.keys() for x in self.basicCols):
            raise streamexceptions.InputError('Input df must include keys or columns "exes", "whys", "zees", "Thalweg"')
    
    def __str__(self):
        """
        Prints the name of the Profile object. If the name attribute is None, prints "UNNAMED".
        """
        if self.name:
            return(self.name)
        else:
            return("UNNAMED")
        
    def qplot(self, showThw = True, showWs = True, showBkf = True, showTob = True, showFeatures = False):
        plt.figure()
        if showThw:
            plt.plot(self.filldf['Station'],self.filldf['Thalweg'], color = 'gray', linewidth = 2, label = 'Thalweg')
        plt.title(str(self))
        plt.xlabel('Station (' + self.unitDict['lengthUnit'] + ')')
        plt.ylabel('Elevation (' + self.unitDict['lengthUnit'] + ')')
        
        if 'Water Surface' in self.filldf and showWs:
            plt.plot(self.filldf['Station'],self.filldf['Water Surface'], "b--",
                     color = '#31A9FF', linewidth = 2, label = 'Water Surface')
                     
        if 'Bankfull' in self.filldf and showBkf:
            plt.plot(self.filldf['Station'],self.filldf['Bankfull'],
                     color = '#FF0000', linewidth = 2, label = 'Bankfull')
                     
        if 'Top of Bank' in self.filldf and showTob:
            plt.plot(self.filldf['Station'],self.filldf['Top of Bank'],
                     color = '#FFBD10', linewidth = 2, label = 'Top of Bank')
                     
        if showFeatures:
            for morph in self.features:
                for feat in self.features[morph]:
                    feat.addplot()
                     
        handles,labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels,handles))
        plt.legend(by_label.values(),by_label.keys())
    
    def planplot(self):
        """
        Uses matplotlib to create a quick plot of the planform of the profile.
        """
        plt.figure()
        plt.plot(self.df['exes'],self.df['whys'])
        plt.title(str(self) + ' (Planform)')
        plt.xlabel('Easting (' + self.unitDict['lengthUnit'] + ')')
        plt.ylabel('Northing (' + self.unitDict['lengthUnit'] + ')')

    def generate_stationing(self):
        stations = sm.get_stationing(self.df['exes'],self.df['whys'],project = False)
        self.filldf['Station'] = stations
        
    def fill_name(self,name):
        """
        Given a column name/key, interpolates all missing values.
        """
        result = sm.interpolate_series(self.filldf['Station'],self.filldf[name])
        return(result)
        
    def fill_columns(self):
        """
        Interpolates missing values in columns with names contained in fillCols
        """
        for col in self.fillCols:
            if col in self.filldf:
                self.filldf[col] = self.fill_name(col)
    
    def split_morph(self, morphType):
        """
        Given a morph type contained in self.morphCols, returns a list of Feature objects
        representing that feature type.
        
        PROBLEM: if a morph is broken by another morph that is two shots long
        then this will fail. Additionally, isolated morphs that are only two shots long
        are swallowed by Unclassified.
        """
        if morphType not in self.filldf:
            return([])
        featureIndices = sm.crush_consecutive_list(sm.make_consecutive_list(self.filldf[morphType], indices = True))
        morphList = [Feature(self.filldf[sliceInd[0]:sliceInd[1]],
                             name=f'{self.name}, {morphType} {i}',
                             metric = self.metric,
                             morphType = morphType) for i,sliceInd in enumerate(featureIndices)]
        return(morphList)
        
    def create_features(self):
        featDict = {morph:self.split_morph(morph) for morph in self.morphCols}
        self.features = featDict
        
    def make_unclassified(self):
        """
        Makes a column indicating rows that do not have a specified substrate feature.
        """
        # STILL NOT QUITE CORRECT
        mList = []
        for name in self.morphCols[:-1]:
            try:
                mList.append(sm.crush_consecutive_list(sm.make_consecutive_list(self.filldf[name]),offset=0))
            except KeyError:
                next
        
        allTogether = []
        for inner in mList:
            for el in inner:
                allTogether.append(el)
        
        allSort = sorted(allTogether,key=lambda x:x[0]) # sort by first element in tuple
        
        missing = []
        for i,_ in enumerate(allSort):
            try:
                tup1 = allSort[i]
                tup2 = allSort[i+1]
            except IndexError: # when tup1 is the last tuple
                break
            
            if tup1[1] != tup2[0]:
                rList = [i for i in range(tup1[1],tup2[0]+1)]
                missing.append(rList)
           
        nShots = len(self.filldf['Thalweg'])-1
        if allSort[-1][1] != nShots:
            missing.append([i for i in range(allSort[-1][1],nShots+1)])
        if allSort[0][0] != 0:
            missing.append([i for i in range(0,allSort[0][0])+1])
        
        missingSorted = sorted(missing,key=lambda x:x[0])
        missingUnpacked = []
        for el in missingSorted:
            missingUnpacked.extend(el)
                
        unclassed = [None]*len(self.filldf['Thalweg'])    
        for i,val in enumerate(missingUnpacked):
            unclassed[val] = self.filldf['Thalweg'][val]
            
        self.filldf['Unclassified'] = unclassed
        
    def make_elevations_agree(self,colName):
        """
        Makes the corresponding col value in a row agree with the thalweg value in that row.
        """
        pass
    
    def insert_shot(self):
        pass
    
    def modify_shot(self):
        pass
    
    def make_length(self):
        pass
        
    
class Feature(Profile):
    """
    A subsection of a longitudinal stream profile representing a distinct morphological substrate feature.
     
    Attributes:
        x
    """
    
    morphColors = {'Unclassified':'black',
                   'Riffle':'red',
                   'Run':'yellow',
                   'Pool':'blue',
                   'Glide':'green'}
    
    def __init__(self, df, name = None, metric = False, morphType = None):
        Profile.__init__(self, df, name, metric = False)
        self.morphType = morphType
        
    def addplot(self):
        """
        Adds scatter points and lines representing the feature to a plot.
        """
        plt.plot(self.filldf['Station'],self.filldf[self.morphType],
                 color = self.morphColors[self.morphType], linewidth = 2,label='_NOLABEL_')
        plt.scatter(self.filldf['Station'],self.filldf[self.morphType],
                    color = self.morphColors[self.morphType])
        
        # code block below updates the legend, but ignores the label if it's a duplicate
        handles,labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels,handles))
        plt.legend(by_label.values(),by_label.keys())
        
        