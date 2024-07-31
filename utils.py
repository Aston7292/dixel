'''
collections of shared funcs/dataclasses
'''

from dataclasses import dataclass

@dataclass
class Point:
    '''
    dataclass for representing the coordinates of a 2d point
    '''

    x: int
    y: int

@dataclass
class Size:
    '''
    dataclass for representing the size of a 2d object
    '''

    w: int
    h: int
