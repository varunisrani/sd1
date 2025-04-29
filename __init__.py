"""
SD1 - Film Production AI System
A comprehensive module for film production automation.
"""

__version__ = '1.0.0'
__author__ = 'Varun Israni'

import os
import sys

# Add the root directory to path so that imports work correctly
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR) 
