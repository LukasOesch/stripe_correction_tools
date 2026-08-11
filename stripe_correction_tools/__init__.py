#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 13:18:34 2026

@author: loesch
"""

from .utils import are_stripes_present, find_buffer_indices, shift_stripes
try:
    from .labdata_correction_plugin import MiniscopeStripeCorrection
except:
    print('Missing dependencies, labdata plugin was not imported')