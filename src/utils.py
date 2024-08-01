'''
collections of shared funcs/dataclasses
'''

from dataclasses import dataclass
from typing import Tuple

@dataclass
class Point:
    '''
    dataclass for representing the coordinates of a point
    takes x and y
    '''

    x: int
    y: int

    @property
    def xy(self) -> Tuple[int, int]:
        '''
        returns x and y as a tuple
        '''

        return (self.x, self.y)

@dataclass
class RectPos:
    '''
    dataclass for representing the position of a rect
    takes x and y as tuple and the value they represent (e.g. topleft)
    '''

    xy: Tuple[int, int]
    pos: str

@dataclass
class Size:
    '''
    dataclass for representing the size of a object
    takes width and height
    '''

    w: int
    h: int

    @property
    def size(self) -> Tuple[int, int]:
        '''
        returns w and h as a tuple
        '''

        return (self.w, self.h)
