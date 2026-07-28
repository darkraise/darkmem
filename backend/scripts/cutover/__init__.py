"""One-time cutover transform from the brownfield ``0006`` schema onto the
rebuilt ``0001_baseline`` schema.

This package builds the transform. It never runs it against production: the
rehearsal on a dump copy is T1.53's and the real execution is T1.54's.
"""
