# -*- coding: utf-8 -*-
"""
Created on Sat Jul 13 11:19:19 2019

@author: danie
"""

import os
import pickle
import re
from pathlib import Path
try:
    from sobek import read
    from sobek import write
except:
    import read
    import write
import shutil


def _get_layer(path,cache,layer_name,crs=None):
    cache_file = cache.joinpath(f'{layer_name}.p')
    if cache_file.exists():
        with open(str(cache_file), "rb") as src:
            result = pickle.load(src)
    else:
        reader = getattr(read,layer_name)
        if crs:
            result = reader(path,crs)
        else:
            result = reader(path)
        with open(str(cache_file), "wb") as dst: 
            pickle.dump(result, dst)
    return result   
                
class Project(object):
    
    def __init__(self, path):
        with open(os.path.join(os.path.abspath(path),'caselist.cmt'),'r') as CSV:
            self.crs = 'epsg:28992'
            self.path = Path(path)
            self.cache = Path(path,'fixed\python_cache').absolute().resolve()
            if not os.path.exists(self.cache): os.mkdir(self.cache)
            self.__case_list = {}
            for line in CSV.readlines():
                line_split = re.split(r" '",line.replace("'\n",""))
                self.__dict__.update({line_split[1]:None})
                self.__case_list[line_split[1]] = line_split[0]

    def __getitem__(self, key):
        if key in list(self.__dict__.keys()):
            path = self.path.joinpath(self.__case_list[key])
            cache = self.cache.joinpath(self.__case_list[key])
            if not os.path.exists(cache): os.mkdir(cache)
            return Case(key, path, crs=self.crs, cache = cache)
        else: print(key, 'not a case in this project')

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def get_cases(self):
        return([case  for case in self.__dict__.keys() if case in self.__case_list.keys()])
        
    def drop_cache(self):
        if self.cache.exists():
            shutil.rmtree(self.cache)
        self.cache.mkdir()
            
class Case(object):
    
    def __init__(self,name,path,crs,cache):
        self.crs = crs
        self.path = path
        self.name = name
        self.network = Network(path,cache,crs)
        self.parameters = Parameters(path,cache) 
        self.results = Results(path,cache) 
        self.boundaries = Boundaries(path,cache)
        self.control = _get_layer(path, cache,'control')
        
    def to_kisters(self,name,link_classes=None,extra_params=dict(),prefix='',initials=False):
        write.kisters(self,
                      name=name,
                      link_classes=link_classes,
                      extra_params=extra_params,
                      prefix=prefix,
                      initials=initials)

class Network(object):
    
    def __init__(self,path,cache,crs):
        result = _get_layer(path, cache,'network',crs=crs)
        self.links = result['links']
        self.nodes = result['nodes']
        self.objects = result['objects']
        self.segments = result['segments']
        
class Parameters(object):
    def __init__(self,path,cache):
        result = _get_layer(path,cache,'parameters')
        self.friction = result['friction']
        self.structures = result['structures']
        self.cross_sections = result['cross_sections']

class Boundaries(object):
    def __init__(self,path,cache):
        result = _get_layer(path, cache,'boundaries')
        self.flow = result['flow']
               
class Results(object):
    
    def __init__(self,path,cache):
        result = _get_layer(path, cache,'results')
        self.points = result['points']
        self.links = result['links']
        self.structures = result['structures']
        
def test():
    path = r'c:\SK215003\GIETERVE.lit'
    case = 'Default'
    project = Project(path)
    project.drop_cache()
    return project[case]
    